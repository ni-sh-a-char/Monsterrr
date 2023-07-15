import discord
from discord.ext import commands
import requests
import json
import paramiko

bot = commands.Bot(command_prefix='!')

# Define the SSH connection parameters
SSH_HOST = 'remote-server.com'
SSH_PORT = 22
SSH_USERNAME = 'your-username'
SSH_PASSWORD = 'your-password'

# Create an SSH client
ssh_client = paramiko.SSHClient()
ssh_client.load_system_host_keys()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')


@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author.name}!')


@bot.command()
async def info(ctx):
    server = ctx.guild
    await ctx.send(f'Server Name: {server.name}')
    await ctx.send(f'Server ID: {server.id}')
    await ctx.send(f'Total Members: {server.member_count}')


@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    if ctx.author.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await ctx.send(f'{member.name} has been kicked.')
    else:
        await ctx.send('You do not have permission to kick members.')


@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    if ctx.author.guild_permissions.ban_members:
        await member.ban(reason=reason)
        await ctx.send(f'{member.name} has been banned.')
    else:
        await ctx.send('You do not have permission to ban members.')


@bot.command()
async def clear(ctx, amount=5):
    if ctx.author.guild_permissions.manage_messages:
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f'{amount} messages have been cleared.')
    else:
        await ctx.send('You do not have permission to clear messages.')


@bot.command()
async def join(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()
        await ctx.send(f'Joined {channel}')
    else:
        await ctx.send('You are not connected to a voice channel.')


@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Left the voice channel.')
    else:
        await ctx.send('I am not connected to a voice channel.')


@bot.command()
async def fetch_data(ctx):
    # Make an API request
    try:
        response = requests.get("https://api.example.com/data")
        data = response.json()

        # Format the JSON response for presentation
        formatted_data = json.dumps(data, indent=4, sort_keys=True)

        # Send the formatted data as a response
        await ctx.send(f"Data:\n```json\n{formatted_data}\n```")
    except requests.RequestException as e:
        await ctx.send(f"Failed to fetch data from the API: {str(e)}")


@bot.command()
async def execute_command(ctx, *, command):
    if ctx.author.id == YOUR_USER_ID:  # Replace with your own user ID for authorization
        try:
            # Connect to the remote server
            ssh_client.connect(SSH_HOST, port=SSH_PORT, username=SSH_USERNAME, password=SSH_PASSWORD)

            # Execute the command on the remote server
            stdin, stdout, stderr = ssh_client.exec_command(command)

            # Get the output and error streams
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            # Send the output and error as separate messages
            await ctx.send(f'Output:\n```\n{output}\n```')
            if error:
                await ctx.send(f'Error:\n```\n{error}\n```')
        except paramiko.AuthenticationException:
            await ctx.send('Authentication failed. Please check your credentials.')
        except paramiko.SSHException as e:
            await ctx.send(f'SSH connection failed: {str(e)}')
        finally:
            # Close the SSH connection
            ssh_client.close()
    else:
        await ctx.send('You are not authorized to use this command.')


bot.run('YOUR_BOT_TOKEN')
