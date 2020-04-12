from discord.ext import commands
import discord
import asyncio
import random
import time

class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.counting_channels = {}
        self.records = {}
        self.kicked_member_roles = {}
        
    @commands.command(name='sorry')
    async def sorry_command(self,ctx):
        member = ctx.message.author
        if not member.id in self.kicked_member_roles.keys():
            return
        for role in self.kicked_member_roles.get(member.id,[]):
            await member.add_roles(role)

        end = "!" if len(self.kicked_member_roles[member.id]) == 0 else  ", your previous roles have been restored."
        await ctx.message.channel.send(f"{member.mention} Thanks for apologizing"+end)
        self.kicked_member_roles.pop(member.id,None)
    
        
    @commands.command()
    async def startcounting(self,ctx,number:int=0):
        self.counting_channels[ctx.message.channel.id] = number
        
    @commands.command()
    async def stopcounting(self,ctx):
        idx = None
        for i,channel_id in enumerate(self.counting_channels):
            if ctx.message.channel.id in channel_id.keys():
                idx = i
                break
        if idx:
            self.counting_channels.pop(ctx.message.channel.id, None)
    
    @commands.command()
    async def resetcounting(self,ctx):
        self.counting_channels = {}
        
    def aristocrat(self):
        for channel_id in self.counting_channels.values():
            try:
                bot.get_channel(channel_id[0])
            except:
                self.counting_channels.pop(channel_id, None)
    
    
    def addpoint(self,member_id):
        if not self.records.get(member_id,None):
            self.records[member_id] = 1
            return
        self.records[member_id] += 1
    

    
    
    @commands.Cog.listener()
    async def on_message(self,message):
        if not message.channel.id in self.counting_channels.keys() or message.author.bot:
            return
        try:
            if not message.content.isdigit():
                await message.delete()
                return
            number = int(message.content)
        except:
            await message.delete()
            return
            
        if number != self.counting_channels[message.channel.id]+1:
            
            if len(message.author.roles) > 1:
                self.kicked_member_roles[message.author.id] = [role for role in list(message.author.roles)[1:]]
                
            invite = await message.channel.create_invite(reason="Everyone makes mistakes.",max_uses=1)
            
            try:
                await message.author.send(f"You miscounted, next number is {self.counting_channels[message.channel.id]+1}, not {number}! If you want to join back use this link: {invite.url}")
            except:
                pass
            await message.author.kick()
            await message.delete()
            return
        
            
        self.addpoint(message.author.id)
        self.counting_channels[message.channel.id] = number
        
    
    @commands.Cog.listener()
    async def on_member_join(self,member):
        if member.id in self.kicked_member_roles.keys():
            await member.send(f"To regain your previous roles type: `pls sorry`")
        
def setup(_bot):
    cog = Counting(_bot)
    _bot.add_cog(cog)