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
    id = Column(Integer,primary_key=True)
    member_id = Column(BigInteger)
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
        self.kicked_members = {}
        self.watched_message_ids = []
        self.no_delete = []
        
    @commands.command(name='sorry',aliases=['forgive'])
    async def sorry_command(self,ctx):
        member = ctx.message.author
        
        stuff = self.kicked_members.get(member.id,None)
        if not stuff:
            return
        self.kicked_members.pop(member.id)
        
        roles = stuff['roles']
        nick = stuff['nick']
        
        end_content = []
        if roles:
            for role in roles:
                await member.add_roles(role)
            end_content.append(f"{len(roles)} roles")
        if nick:
            await member.edit(nick=nick)
            end_content.append(f"nickname")

        end = "!"
        if end_content:
            e = " and ".join(end_content)
            end = f", you regained your previous {e}."
            
        channel = ctx.message.guild.system_channel if ctx.message.guild.system_channel else member
            
        await channel.send(f"{member.mention} Thanks for apologizing"+end)
        
        
    @commands.command(name='purge')
    async def clean_command(self,ctx):
        await self.purgechannel(ctx.message.channel)
        
    @commands.command(name='load')
    async def load_command(self,ctx): 
        await self.loadLastMessagePerChannel(self,channel=None)
        
    async def purgechannel(self,channel):
        cat_id = channel.category_id
        category = None
        for c in channel.guild.categories:
            if c.id == cat_id:
                category = c
        if category:
            c = await category.create_text_channel(channel.name)
            await c.edit(position=channel.position)
            await channel.delete()
        
        await self.loadLastMessagePerChannel()
    
    async def loadLastMessagePerChannel(self,channel=None):
        def predicate(message):
            return message.content.isdigit()
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if 'counting' in channel.name:
                    self.counting_channels[channel.id] = {}
                    print(f"ADDED CHANNEL {channel.name}")
                    to_del = []
                    found = False
                    async for elem in channel.history(limit=100).filter(predicate):
                        if predicate(elem):
                            self.counting_channels[channel.id]['last_message'] = elem
                            self.counting_channels[channel.id]["current_value"] = int(elem.content)
                            print(f"SET LAST VALUE TO  {int(elem.content)}")
                            found = True
                            break
                        else:
                            to_del.append(elem)
                    if not found:
                        self.counting_channels[channel.id]['last_message'] = None
                        self.counting_channels[channel.id]["current_value"] = 0
                    await channel.delete_messages(to_del)
                                
                
    @commands.command()
    async def startcounting(self,ctx,number:int=0):
        self.counting_channels[ctx.message.channel.id] = {}
        self.counting_channels[ctx.message.channel.id]["current_value"] = number
        self.counting_channels[ctx.message.channel.id]['last_message'] = None
        
        
    # @commands.command()
    # async def reset(self,ctx):
        
    
    @commands.command()
    async def rank(self,ctx):
        return
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

    def addkmember(self,member):
        if member.id in self.kicked_members.keys():
            return False
        self.kicked_members[member.id] = {"roles": None, "nick": None}
        return True
    
    @commands.Cog.listener()
    async def on_message(self,message):
        if not message.channel.id in self.counting_channels.keys() or message.author.id == self.bot.user.id:
            return
        member = message.author
        try:
            if not message.content.isdigit() or message.content.startswith("0"):
                self.no_delete.append(message.id)
                await message.delete()
                return
            number = int(message.content)
        except:
            self.no_delete.append(message.id)
            await message.delete()
            return
            
        if number != self.counting_channels[message.channel.id]['current_value']+1:
            added = self.addkmember(member)
            
            if added:
                if len(member.roles) > 1:
                    self.kicked_members["roles"] = [role for role in list(member.roles)[1:]]
                if member.display_name != member.name:
                    self.kicked_members["nick"] = member.display_name
                
            invite = await message.channel.create_invite(reason="Everyone makes mistakes.",max_uses=1)
            
            try:
                await member.send(f"You miscounted, next number is {self.counting_channels[message.channel.id]['current_value']+1}, not {number}! Everyone makes mistakes, feel free to join back after you rethink your life choices: {invite.url}")
            except:
                pass
            try:
                await member.kick()
            except:
                pass
            self.no_delete.append(message.id)
            await message.delete()
            return
         
        self.counting_channels[message.channel.id]['current_value'] = number

        stats = MemberStats.get(member,member.guild)
        stats.addPoints()
        
        lm = self.counting_channels[message.channel.id].get("last_message")
        if not lm or lm.author.id == member.id:
            stats.addStreak()
        else:
            stats.setStreak(1)
        stats.lastCountedNumber = number
        
        
        self.counting_channels[message.channel.id]['last_message'] = message
        
        DatabaseHandler.commit()
    
    
    
    @commands.Cog.listener()
    async def on_member_join(self,member):
        km = self.kicked_members.get(member.id)
        if km:
            await member.send(f"To regain your previous roles and name type: `pls sorry`")
    
    @commands.Cog.listener()
    async def on_message_delete(self,message):
        counting_channel_id = self.counting_channels.get(message.channel.id, None)
        if not counting_channel_id or message.id in self.no_delete:
            self.no_delete.remove(message.id)
            return
        last_mess = self.counting_channels[message.channel.id]['last_message']
        try:
            await message.author.kick()
        except:
            pass
        if not last_mess:
            return
        
        if last_mess.id == message.id:
            messge = await message.channel.send(message.content)
            self.counting_channels[message.channel.id]['last_message'] = message
            invite = await message.channel.create_invite(max_uses=1)
            await message.author.send(f"Don't do that again please: {invite.url}")
        else:
            self.counting_channels[message.channel.id]['last_message'] = None
            self.counting_channels[message.channel.id]['current_value'] = 0
            await message.guild.system_channel.send(f"{message.author.mention} Fucked up entire counting process by deleting number **{message.content}**. Go play with your dad's dick like you always do {message.author.mention}.")
            await self.purgechannel(message.channel)
            
            
    @commands.Cog.listener()
    async def on_raw_message_delete(self,message):
        if message.channel_id in self.counting_channels.keys():
            if not message.cached_message:
                try:
                    await message.author.kick()
                except:
                    pass
                channel = self.bot.get_channel(message.channel_id)
                await channel.guild.system_channel.send(f"Someone fucked up entire counting process by deleting a message. Go play with your dad's dick like you always do you message-deleting cunt, go kys.")
                await self.purgechannel(channel)
            
    @commands.Cog.listener()
    async def on_raw_message_edit(self,message):
        if message.channel_id in self.counting_channels.keys():
            if not message.cached_message:
                try:
                    await message.author.kick()
                except:
                    pass
                message = await self.bot.get_channel(message.channel_id).fetch_message(message.message_id)
                await message.guild.system_channel.send(f"{message.author.mention} Fucked up entire counting process by editing a message. Go play with your dad's dick like you always do {message.author.mention}.")
                await self.purgechannel(message.channel)

    @commands.Cog.listener()
    async def on_message_edit(self,before,after):
        # if not message.cached_message:
        #     message = await self.bot.fetch_message(message.message_id)
        message = before
        counting_channel = self.counting_channels.get(message.channel.id, None)
        if not counting_channel or message.id in self.watched_message_ids:
            return
        last_mess = self.counting_channels[message.channel.id]['last_message']
        if after.id == last_mess.id:
            self.no_delete.append(after.id)
            await after.delete()
            message = await before.channel.send(before.content)
            self.counting_channels[message.channel.id]['last_message'] = message
            return
        self.watched_message_ids.append(message.id)
        desired_content = message.content
        time = random.randint(5,60)
        embed = discord.Embed(description = f"You edited [this message]({message.jump_url}), it doesn't meet our counting standards.\nRevert it back to its original value ({message.content}) in `{time}` seconds and you won't be kicked.",color=discord.Colour.from_rgb(255,0,0))
        await message.author.send(embed=embed)
        await asyncio.sleep(time)
        if after.content != desired_content:
            try:
                await after.author.kick()
            except:
                pass
            
            await self.purgechannel(message.channel)
            await message.guild.system_channel.send(f"{message.author.mention} Fucked up entire counting process by editing a message. Go play with your dad's dick like you always do {message.author.mention}.")
           
        else:
            await after.author.send(embed=discord.Embed(description = f"Thank You for editing your message.",color=discord.Colour.from_rgb(0,255,0)))
        self.watched_message_ids.remove(after.id)
        
            
    @commands.Cog.listener()
    async def on_ready(self):
        DatabaseHandler.init();
        DatabaseHandler.createTables();
        await self.loadLastMessagePerChannel()
        print("Everything loaded")
        
def setup(_bot):
    cog = Counting(_bot)
    _bot.add_cog(cog)