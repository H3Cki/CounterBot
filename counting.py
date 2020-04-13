from discord.ext import commands
import discord
import asyncio
import random
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, ForeignKey, Float, Integer, BigInteger, String, TIMESTAMP, Boolean

class DatabaseHandler:
    Base = declarative_base()
    session = None

    @classmethod
    def init(cls,url="sqlite:///counting_db.db"):
        cls.engine = create_engine(url,echo=False)
        cls.newSession()

    @classmethod
    def createTables(cls):
        cls.Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def newSession(cls):
        Session = sessionmaker(bind=cls.engine,expire_on_commit=False)
        cls.session = Session()

    @classmethod
    def commit(cls):
        cls.session.commit()

    @classmethod
    def delete(cls,item):
        cls.session.delete(item)

    @classmethod
    def closeSession(cls):
        cls.session.close()

    @classmethod
    def add(cls, item):
        cls.session.add(item)
        cls.session.commit()

    @classmethod
    def getTables(cls):
        print(cls.Base.metadata.tables.keys())


class MemberStats(DatabaseHandler.Base):
    __tablename__ = "stats"
    member_id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger)
    points = Column(Integer)
    streak = Column(Integer)
    longestStreak = Column(Integer)
    lastCountedNumber = Column(Integer)
    last_streak_message_id = Column(BigInteger)
    
    def __init__(self,member):
        self.member_id = member.id
        self.guild_id = member.guild.id
        self.points = 0
        self.streak = 0
        self.longestStreak = 0
        self.last_streak_message_id = 0
    
    def addPoints(self,val=1):
        self.points += val
    
    def addStreak(self,val=1):
        self.streak += val
        self.checkLongest()
        
    def setStreak(self,val=1):
        self.streak = 1
        self.checkLongest()
        
    def checkLongest(self):
        if self.streak > self.longestStreak:
            self.longestStreak = self.streak
    
    @classmethod
    def get(cls,member=None,guild=None):
        if member is None:
            q = DatabaseHandler.session.query(MemberStats)
            if guild:
                q.filter(MemberStats.guild_id==guild.id)
            return q.all()
        result = DatabaseHandler.session.query(MemberStats).filter(MemberStats.member_id == member.id,MemberStats.guild_id == guild.id).first()
        if not result:
            result = MemberStats(member)
            DatabaseHandler.add(result)
        return result

class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.counting_channels = {}
        self.records = {}
        self.kicked_member_roles = {}
        self.kicked_member_names = {}
        self.previous_message = None
        
    @commands.command(name='sorry',aliases=['forgive'])
    async def sorry_command(self,ctx):
        member = ctx.message.author
        if member.id in self.kicked_member_roles.keys():
            if member.id in self.kicked_member_names.keys():
                await member.edit(name=self.kicked_member_names[member.id])
                self.kicked_member_names.pop(member.id,None)
            for role in self.kicked_member_roles.get(member.id,[]):
                await member.add_roles(role)

            end = "!" if len(self.kicked_member_roles[member.id]) == 0 else  ", your previous roles have been restored."
            

            channel = ctx.message.guild.system_channel if ctx.message.guild.system_channel else member
                
            await channel.send(f"{member.mention} Thanks for apologizing"+end)
            self.kicked_member_roles.pop(member.id,None)
            
    @commands.command(name='clean')
    async def clean_command(self,ctx):
        await self.clean()
        
        
    async def clean(self):
        def predicate(message):
            return message.content.isdigit()
        for channel_id in self.counting_channels.keys():
            channel = self.bot.get_channel
            to_del = []
            async for elem in channel.history(limit=None).filter(not predicate):
                to_del.append(elem)
            await channel.delete_messages(to_del)
    
    
    async def loadLastMessagePerChannel(self):
        def predicate(message):
            return message.content.isdigit()
        for channel_id in self.counting_channels.keys():
            channel = self.bot.get_channel
            to_del = []
            async for elem in channel.history(limit=None).filter(predicate):
                if predicate(elem):
                    self.counting_channels[channel.id]['last_message_author_id'] = elem.author.id
                    break
    
                            
                
    @commands.command()
    async def startcounting(self,ctx,number:int=0):
        self.counting_channels[ctx.message.channel.id] = {}
        self.counting_channels[ctx.message.channel.id]["current_value"] = number
        self.counting_channels[ctx.message.channel.id]["last_message_author_id"] = None
        
        
    # @commands.command()
    # async def stopcounting(self,ctx):
    #     idx = None
    #     for i,channel_id in enumerate(self.counting_channels):
    #         if ctx.message.channel.id in channel_id.keys():
    #             idx = i
    #             break
    #     if idx:
    #         self.counting_channels.pop(ctx.message.channel.id, None)
    
    
    @commands.command()
    async def rank(self,ctx):
        all_stats = MemberStats.get(guild=ctx.message.guild)
        all_stats = sorted(all_stats,key = lambda x: (x.points,x.longestStreak), reverse=True)
        if len(all_stats) > 10:
            all_stats = all_stats[:11]
        t = ""
        top3 = ["🥇","🥈","🥉"]
        extra = "🔹"
        mx = [channel.id for channel in ctx.message.guild.channels]
        c = None
        for channel_id in mx:
            c = self.counting_channels.get(channel_id,None)
            if c:
                break
        val = c['current_value'] if c else 0
        embed = discord.Embed(title=f"Counting Competition in {ctx.message.guild.name} - {val}")
        #embed.set_thumbnail(url=)
        for i,stat in enumerate(all_stats):
            guild = self.bot.get_guild(stat.guild_id)
            member = guild.get_member(stat.member_id)
            emoji = top3[i] if i < 3 else extra
            t += f"{emoji} **{member.display_name}** Counted: `{stat.points}` Times\n<:blank:551400844654936095>[Streak] Current `{stat.streak}`/`{stat.longestStreak}` Longest\n<:blank:551400844654936095>Last number counted: `{stat.lastCountedNumber}`\n"
        embed.description = t
        await (ctx.message.guild.system_channel or ctx.message.author).send(embed=embed)
        
    @commands.command()
    async def resetcounting(self,ctx):
        self.counting_channels = {}
        

    @commands.command()
    async def destreak(self,ctx):
        await ctx.send(str(self.counting_channels[ctx.message.channel.id]['current_value']+1))


    
    
    @commands.Cog.listener()
    async def on_message(self,message):
        if not message.channel.id in self.counting_channels.keys():
            return
        member = message.author
        try:
            if not message.content.isdigit():
                await message.delete()
                return
            number = int(message.content)
        except:
            await message.delete()
            return
            
        if number != self.counting_channels[message.channel.id]['current_value']+1:
            
            if len(member.roles) > 1:
                self.kicked_member_roles[member.id] = [role for role in list(member.roles)[1:]]
            if member.display_name != member.name:
                self.kicked_member_names[member.id] = member.display_name
                
            invite = await message.channel.create_invite(reason="Everyone makes mistakes.",max_uses=1)
            
            try:
                await member.send(f"You miscounted, next number is {self.counting_channels[message.channel.id]['current_value']+1}, not {number}! Feel free to join back after you rethink your life choices: {invite.url}")
            except:
                pass
            await member.kick()
            await message.delete()
            return
         
        self.counting_channels[message.channel.id]['current_value'] = number

        stats = MemberStats.get(member,member.guild)
        stats.addPoints()
        if self.counting_channels[message.channel.id].get("last_message_author_id",member.id) == member.id:
            stats.addStreak()
        else:
            stats.setStreak(1)
        stats.lastCountedNumber = number
        
        
        self.counting_channels[message.channel.id]['last_message_author_id'] = member.id
        
        DatabaseHandler.commit()
    
    @commands.Cog.listener()
    async def on_member_join(self,member):
        if member.id in self.kicked_member_roles.keys():
            await member.send(f"To regain your previous roles and name type: `pls sorry`")
            
            
    @commands.Cog.listener()
    async def on_ready(self):
        DatabaseHandler.init();
        DatabaseHandler.createTables();
        await self.loadLastMessagePerChannel()
        
def setup(_bot):
    cog = Counting(_bot)
    _bot.add_cog(cog)