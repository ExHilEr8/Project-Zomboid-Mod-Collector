import requests
import traceback
import os
import re
import discord
import csv
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SERVER = int(os.getenv('DISCORD_SQUEEBS_SERVER'))
STEAMKEY = os.getenv('STEAM_API_KEY')

defaultlink = 'https://steamcommunity.com/sharedfiles/filedetails/?id=2848719424'

bot = commands.Bot(command_prefix='!', intents = discord.Intents.all())

@bot.event
async def on_ready():
    guild = bot.get_guild(SERVER)
    
    print(f'{bot.user} has connected to {guild.name} ({guild.id}).')
    
    members = '\n - '.join([member.name for member in guild.members])
    print(f'Server Members:\n - {members}')


@bot.command(name='collection')
async def get_collection_lists(ctx, collectionLink):
    collectionID = collectionLink.split('?id=')[1]

    # Get collection item info
    req = requests.post(f'https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/?key={STEAMKEY}&collectioncount=1&publishedfileids%5B0%5D={collectionID}', data ={'collectioncount': 1, 'publishedfileids[0]':collectionID})
    data = req.json()['response']['collectiondetails'][0]['children']

    # Collection IDs
    collIDs = {}
    
    requrl = 'https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/?key=BC0081D6DF175AB664E31EE74D72C978'
    pfileid_args = ''

    # Collect workshop IDs and build SteamAPI POST request url parameters
    for i, item in enumerate(data):
        collIDs[f'publishedfileids[{i}]'] = item['publishedfileid']
        pfileid_args += f'&publishedfileids%5B{i}%5D={i}' 
    
    # Add item count to POST request data
    collIDs_length = len(collIDs)
    collIDs['itemcount'] = collIDs_length

    # Build POST request URL
    requrl += '&itemcount=' + str(collIDs_length)
    requrl += pfileid_args
    
    req = requests.post(requrl, collIDs)
    moddata = req.json()['response']['publishedfiledetails']

    workshop_str = ''
    mod_str = ''
    
    try:
        for mod in moddata:
            skip = False
            
            workshopID = mod['publishedfileid']
            modID = ''
            
            # Check exclusion file to determine if the item should be skipped
            with open('Project Zomboid Mod Collector\\exclude.txt', 'r') as excfile:
                lines = excfile.readlines()
                
                for line in lines:
                    if workshopID + '\n' == line:
                        skip = True
            
            if skip == True: continue
            
            # Check inclusion file to determine if a manually entered ID exists
            with open('Project Zomboid Mod Collector\\include.csv', 'r') as incfile:
                reader = csv.DictReader(incfile)
                
                for line in reader:
                    if workshopID == line['workshopID']:
                        workshopID = line['workshopID']
                        modID = line['modID']
            
            # If the mod isnt excluded or included previously, determine the Mod ID
            if modID == '':
                # Regex search matches: "Workshop ID: {7-12 long int}\r\nMod ID: {any string, stops at \n}"         
                match = re.search(r"(?i)workshop ?id: \d{7,12}\r?\n? ?mod ?id: .+", mod['description'])
                
                # Fetch the Mod ID from the regex match
                IDString = match.group(0)
                modIDString = IDString.split("\n")[1]
                modID = modIDString.split(": ")[1]
            
            workshop_str += workshopID.rstrip() + ';'
            mod_str += modID.rstrip() + ';'
            
            final_str = '```Workshop ID List:\n' + workshop_str + '\n\n\nMod ID List:\n' + mod_str+'```'
        
        # Send lists as a text file if they exceed the discord maximum character limit
        if(len(final_str) >= 2000):
            tempfpath = 'Project Zomboid Mod Collector\\' + getID_from_link(collectionLink) + '.txt'
            
            with open(tempfpath, 'w') as tempf:
                tempf.write('Workshop IDs:\n' + workshop_str + '\n\n')
                tempf.write('Mod IDs:\n' + mod_str)   
            
            await ctx.send(file=discord.File(tempfpath), content='List length exceeds 2000 characters, had to send as text file:')
            os.remove(tempfpath)
                
        else: await ctx.send(final_str)
            
    except Exception:
        traceback.print_exc()
        
        # Exception warns of mod with unfindable Mod ID
        await ctx.send('Error: ID not found for ' + collectionLink + '\n\n\n' + traceback.format_exc())
  
@bot.command(name='default')
async def get_default_list(ctx):
    await get_collection_lists(ctx, defaultlink)

# Add a Workshop ID to the exclusion list
@bot.command(name='exclude')
async def exclude(ctx, itemLink):
    with open('Project Zomboid Mod Collector\\exclude.txt', 'a', newline='') as f:
        f.write(getID_from_link(itemLink) + '\n')

# Add a Workshop ID to the inclusion list associated with a Mod ID
@bot.command(name='include')
async def include(ctx, itemLink, modID):
    workshopID = getID_from_link(itemLink)
    
    itemTup = (workshopID, modID)
    
    with open('Project Zomboid Mod Collector\\include.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(itemTup)
        
def getID_from_link(link):
    return link.split('?id=')[1]
    
bot.run(TOKEN)