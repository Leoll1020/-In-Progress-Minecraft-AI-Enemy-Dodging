import MalmoPython
import os
import random
import sys
import time
import json
import random
import errno
import math
import Tkinter as tk
from collections import namedtuple
# from ReadMap import *
import ReadMap
import RandomMap
import Constants
import helper

# Mac path problem is not resolved using the following fix
# mapfile = 'map0.txt'
# from ReadMap import readMapTXT
# readMapTXT(os.path.join(os.path.dirname(__file__), mapfile))
# from ReadMap import *

EntityInfo = namedtuple('EntityInfo', 'x, y, z, yaw, pitch, name, colour, variation, quantity')
EntityInfo.__new__.__defaults__ = (0, 0, 0, 0, 0, "", "", "", 1)

import AStarPolicy
import StandardPolicy
import helper
use_random_map = True # True to use random map, false to use mapfiles
mapfiles = ['map0.txt', 'map1.txt', 'map2.txt',
            'map3.txt', 'map4.txt']

num_reps = 100 # has to greater than num_of_map * 10
if use_random_map:
    num_of_map = 5
else:
    num_of_map = len(mapfiles)


recordingsDirectory="FleeRecordings"
try:
    os.makedirs(recordingsDirectory)
except OSError as exception:
    if exception.errno != errno.EEXIST: # ignore error if already existed
        raise

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately

def canvasX(x):
    return (Constants.CANVAS_BORDER/2) + (0.5 + x/float(Constants.ARENA_COL)) * (Constants.CANVAS_WIDTH-Constants.CANVAS_BORDER)

def canvasY(y):
    return (Constants.CANVAS_BORDER/2) + (0.5 + y/float(Constants.ARENA_ROW)) * (Constants.CANVAS_HEIGHT-Constants.CANVAS_BORDER)

def drawMobs(entities, flash):
    canvas.delete("all")
    # if flash:
    #     canvas.create_rectangle(0,0,Constants.CANVAS_WIDTH,Constants.CANVAS_HEIGHT,fill="#ff0000") # Pain.
    # canvas.create_rectangle(canvasX(-Constants.ARENA_COL/2), canvasY(-Constants.ARENA_ROW/2), canvasX(Constants.ARENA_COL/2), canvasY(Constants.ARENA_ROW/2), fill="#888888")
    canvas.create_rectangle(0,0,Constants.CANVAS_WIDTH,Constants.CANVAS_HEIGHT,fill="#666666")
    for ent in entities:
        if ent.name == Constants.MOB_TYPE:
            canvas.create_oval(canvasX(ent.x)-2, canvasY(ent.z)-2, canvasX(ent.x)+2, canvasY(ent.z)+2, fill="#ff2244")
        elif ent.name == Constants.GOAL_TYPE:
            canvas.create_oval(canvasX(ent.x)-3, canvasY(ent.z)-3, canvasX(ent.x)+3, canvasY(ent.z)+3, fill="#4422ff")
        else:
            canvas.create_oval(canvasX(ent.x)-4, canvasY(ent.z)-4, canvasX(ent.x)+4, canvasY(ent.z)+4, fill="#22ff44")
    root.update()

def drawGrids():
    space_width=Constants.CANVAS_WIDTH/float(Constants.ARENA_COL)
    space_height=Constants.CANVAS_HEIGHT/float(Constants.ARENA_ROW)
    for x in range(0,Constants.ARENA_COL+1):
        canvas.create_line(space_height*x,0,space_height*x,Constants.CANVAS_HEIGHT)
    for x in range(0,Constants.ARENA_ROW+1):
        canvas.create_line(0,space_width*x,Constants.CANVAS_WIDTH,space_width*x)
    root.update()

########draw lava##########
def drawLava(map):
    space_width=Constants.CANVAS_WIDTH/float(Constants.ARENA_COL)
    space_height=Constants.CANVAS_HEIGHT/float(Constants.ARENA_ROW)
    lavas=helper.findLava(map)
    for i in lavas:
        w = i[0]+6.5
        h = i[1]+6.5
        canvas.create_rectangle(w*space_width,h*space_height,(w+1)*space_width,(h+1)*space_height,fill='#ffa500')
    root.update()

            
root = tk.Tk()
root.wm_title("Collecting apples, avoiding lava and doging enemies!")



canvas = tk.Canvas(root, width=Constants.CANVAS_WIDTH, height=Constants.CANVAS_HEIGHT, borderwidth=0, highlightthickness=0, bg="white")
canvas.pack()
root.update()


validate = True
# Create a pool of Minecraft Mod clients.
# By default, mods will choose consecutive mission control ports, starting at 10000,
# so running four mods locally should produce the following pool by default (assuming nothing else
# is using these ports):
my_client_pool = MalmoPython.ClientPool()
my_client_pool.add(MalmoPython.ClientInfo("127.0.0.1", 10000))
my_client_pool.add(MalmoPython.ClientInfo("127.0.0.1", 10001))
my_client_pool.add(MalmoPython.ClientInfo("127.0.0.1", 10002))
my_client_pool.add(MalmoPython.ClientInfo("127.0.0.1", 10003))

Constants.agent_host = MalmoPython.AgentHost()
try:
    Constants.agent_host.parse( sys.argv )
except RuntimeError as e:
    print 'ERROR:',e
    print Constants.agent_host.getUsage()
    exit(1)
if Constants.agent_host.receivedArgument("help"):
    print Constants.agent_host.getUsage()
    exit(0)

# if Constants.agent_host.receivedArgument("test"):
if 'test' in sys.argv:
    num_reps = 1

current_yaw = 0
best_yaw = 0
current_life = 0

for iRepeat in range(num_reps):
    # mission_xml = getMissionXML(MOB_TYPE + " Apocalypse #" + str(iRepeat))
    # mission_xml = readMapXML(filename = os.path.dirname(__file__) + '/map0.txt', mode='Creative') #If Windows

    # a is the preference constant between standard policy and a star policy
    # a will be updated every run under same map
    already_killed_by_lava=False
    if iRepeat%(num_reps/num_of_map)==0:  #when start a new map
        Constants.summary[iRepeat/(num_reps/num_of_map)] = []
        Constants.alpha=0
        Constants.candidates = [0, 0.25, 0.5, 0.75, 0.90]
        Constants.step = 0.1
        
        
        if use_random_map:
            
            RandomMap.generate_Matrix()
            mission_xml = RandomMap.randomMapXML(mode=Constants.mode)
        else:
            mission_xml = ReadMap.readMapXML(
                filename = os.path.join(os.path.dirname(__file__), 
                #mapfiles[iRepeat % len(mapfiles)]),    #If cross run
                mapfiles[iRepeat/(num_reps/num_of_map)]), #If not cross run
                mode=Constants.mode)   #If Mac
    helper.print_matrix(Constants.MATRIX)
    my_mission = MalmoPython.MissionSpec(mission_xml,validate)
    max_retries = 3
    for retry in range(max_retries):
        try:
            # Set up a recording
            my_mission_record = MalmoPython.MissionRecordSpec(recordingsDirectory + "//" + "Mission_" + str(iRepeat) + ".tgz")
            my_mission_record.recordRewards()
            # Attempt to start the mission:
            Constants.agent_host.startMission( my_mission, my_client_pool, my_mission_record, 0, "predatorExperiment" )
            break
        except RuntimeError as e:
            if retry == max_retries - 1:
                print "Error starting mission",e
                print "Is the game running?"
                exit(1)
            else:
                time.sleep(2)

    Constants.world_state = Constants.agent_host.getWorldState()
    while not Constants.world_state.has_mission_begun:
        time.sleep(0.1)
        Constants.world_state = Constants.agent_host.getWorldState()

    # break


    Constants.agent_host.sendCommand("move 1")    # run!
    # main loop:
    total_reward = 0
    total_commands = 0
    flash = False

    #a-star policy initialization
    previous_start=(0,0)
    previous_policy=0
    a_star_policy=0
    mob_damage=0
    lava_damage=0
    while Constants.world_state.is_mission_running:
        Constants.world_state = Constants.agent_host.getWorldState()
        if Constants.world_state.number_of_observations_since_last_state > 0:
            msg = Constants.world_state.observations[-1].text
            ob = json.loads(msg)
            
            #print(ob)
           
            if "Yaw" in ob:
                current_yaw = ob[u'Yaw']
            entities = [EntityInfo(**k) for k in ob["entities"]]
            if "Life" in ob:
                life = ob[u'Life']
                if life < current_life:
                    Constants.agent_host.sendCommand("chat aaaaaaaaargh!!!")
                    mob_damage=helper.update_mob_damage(mob_damage)
                    lava_damage,already_killed_by_lava=helper.update_lava_damage(lava_damage,already_killed_by_lava,entities)
                    flash = True
                current_life = life
            if "entities" in ob:
                drawMobs(entities, flash)
                drawLava(Constants.MATRIX)
                drawGrids()
                

                #Memorize where WAS I and what WAS my policy
                try:
                    previous_start=(me.x,me.z) #Not newly born
                except:
                    previous_start=(0,0)
                previous_policy=a_star_policy  #Newely born

                #Where am I now
                me=helper.findUs(entities)

                #Everyone vote!
                a_star_policy=AStarPolicy.a_star((me.x,me.z), current_yaw, Constants.MATRIX, 
                                    previous_start, Constants.AStar_Policy, depth=6)
                standard_policy=StandardPolicy.returnStandardPolicy(entities, current_yaw, current_life)
                best_yaw=helper.choosePolicy(a_star_policy, standard_policy,Constants.MATRIX,entities,(me.x, me.z), Constants.alpha)
                
                print 'best:', best_yaw
                #best_yaw = StandardPolicy.returnStandardPolicy(entities, current_yaw, current_life)
                difference = best_yaw - current_yaw;
                while difference < -180:
                    difference += 360;
                while difference > 180:
                    difference -= 360;
                difference /= 180.0;
                
                
                Constants.agent_host.sendCommand("turn " + str(difference))
                total_commands += 1
                # break
        if Constants.world_state.number_of_rewards_since_last_state > 0:
            # A reward signal has come in - see what it is:
            total_reward += Constants.world_state.rewards[-1].getValue()
            # Constants.agent_host.sendCommand("move 0")    # run!
            # break
        time.sleep(0.02)
        flash = False


    # mission has ended.
    for error in Constants.world_state.errors:
        print "Error:",error.text
    if Constants.world_state.number_of_rewards_since_last_state > 0:
        # A reward signal has come in - see what it is:
        total_reward += Constants.world_state.rewards[-1].getValue()
    print '=================================='
    print "We stayed alive for " + str(total_commands) + " commands, and scored " + str(total_reward)
    print '=================================='
    Constants.summary[iRepeat/(num_reps/num_of_map)].append((total_reward, total_commands, Constants.alpha))
    helper.updateAlpha(mob_damage, lava_damage, 
        Constants.summary[iRepeat/(num_reps/num_of_map)])
    time.sleep(2) # Give the mod a little time to prepare for the next mission.

sum_reward = 0
sum_command = 0
for val in Constants.summary.values():
    for tReward, tCommands,tAlpha in val:
        sum_reward += tReward
        sum_command += tCommands

print Constants.summary

print '=================================='
print 'Summary: average reward: {:10.4f}, average command:{:10.4f}'.format(
                sum_reward / num_reps, sum_command/ num_reps)
print Constants.summary