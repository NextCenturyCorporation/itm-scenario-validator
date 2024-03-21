import yaml, argparse, json, os
from logger import LogLevel, Logger

SCENE_MAP = {
    "sim-jungle": "jungle.yaml",
    "sim-desert": "desert.yaml",
    "sim-urban-sanitized": "urban.yaml",
    "sim-urban": "urban.yaml",
    "sim-sub": "submarine.yaml"
}

CHARACTER_MAP = {
    "casualty_u": "patient U",
    "casualty_v": "patient V",
    "casualty_w": "patient W",
    "casualty_x": "patient X"
}

TREATMENT_MAP = {
    "Nasopharyngeal airway": "Nasal Trumpet",
    "Pain Medications": "Pain Meds",
    "Splint": "Splint",
    "Blood": "Blood",
    "IV Bag": "IV Bag",
    "Burn Dressing": "Burn Dressing",
    "Vented Chest Seal": "Vented Chest Seal",
    "Decompression Needle": "Decompression Needle",
    "Pressure bandage": "Gauze Dressing",
    "Tourniquet": "Tourniquet",
    "Hemostatic gauze": "Hemostatic Gauze"
}


VITALS_ACTIONS = ["SpO2", "Breathing", "Pulse"]
NO_LOCATION = ["Pain Meds", "Blood", "IV Bag", "Nasal Trumpet"]

class ProbeMatcher:
    logger = Logger("probeMatcher")
    soartech_file = None
    adept_file = None
    soartech_yaml = None
    adept_yaml = None
    json_file = None
    json_data = None
    output_soartech = None
    output_adept = None

    def __init__(self, json_path):
        '''
        Load in the file and parse the yaml
        '''
        # get environment from json to choose correct adept/soartech yamls
        self.json_file = open(json_path, 'r')
        self.json_data = json.load(self.json_file)
        pid = self.json_data['participantId']
        pid = pid if pid != '' else self.json_data['sessionId']
        env = SCENE_MAP[self.json_data["configData"]["scene"]]
        # create output files
        try:
            os.mkdir('output')
        except:
            pass
        self.output_soartech = open(os.path.join('output', env.split('.yaml')[0] + f'_soartech_{pid}.json'), 'w')
        self.output_adept = open(os.path.join('output', env.split('.yaml')[0] + f'_adept_{pid}.json'), 'w')
        # get soartech/adept yaml data
        self.soartech_file = open(os.path.join("soartech-evals", env), 'r')
        self.adept_file = open(os.path.join("adept-evals", env), 'r')
        try:
            self.soartech_yaml = yaml.load(self.soartech_file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, "Error while loading in soartech yaml file. Please ensure the file is a valid yaml format and try again.\n\n" + str(e) + "\n")
        try:
            self.adept_yaml = yaml.load(self.adept_file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, "Error while loading in adept yaml file. Please ensure the file is a valid yaml format and try again.\n\n" + str(e) + "\n")


    def __del__(self):
        '''
        Basic cleanup: closing the file loaded in on close.
        '''
        self.logger.log(LogLevel.DEBUG, "Program closing...")
        if (self.soartech_file):
            self.soartech_file.close()
        if (self.adept_file):
            self.adept_file.close()
        if (self.json_file):
            self.json_file.close()
        if (self.output_soartech):
            self.output_soartech.close()
        if (self.output_adept):
            self.output_adept.close()


    def match_probes(self):
        # adept first
        self.check_adept_probes()

        # analyze soartech probes
        self.check_soartech_probes()

    def check_adept_probes(self):
        '''
        Looks through actions and attempts to match them with adept probes
        '''
        print("\n** ADEPT **")
        adept_scenes = self.adept_yaml['scenes']
        start_adept = self.get_scene_by_index(adept_scenes, 0)
        actions = start_adept["action_mapping"]
        for action in actions:
            print(action['action_type'], action['character_id'])

    def check_soartech_probes(self):
        '''
        Finds the closest matching action for each soartech probe
        '''
        print()
        self.logger.log(LogLevel.CRITICAL_INFO, "** SOARTECH **")
        soartech_scenes = self.soartech_yaml['scenes']
        found_all = False
        scene_ind = 0
        action_list_start = 0
        match_data = []
        last_search = False
        first_treatment = False
        while not found_all:
            # get the next scene to find a match in
            scene = self.get_scene_by_index(soartech_scenes, scene_ind)
            if scene is None or action_list_start > len(self.json_data['actionList']):
                found_all = True
                break
            # iterate through all user actions taken
            found_match = False
            matched = None
            for (ind, action_taken) in enumerate(self.json_data['actionList'][action_list_start:]):
                # iterate through all possible actions in the scene
                for probe_action in scene["action_mapping"]:
                    # check for sim sitrep (when "search" is answered for a question)
                    if probe_action['action_type'] == 'SITREP':
                        # if SITREP is a possible action, we are looking for search vs engage. If engage is chosen, we want to log the action for at least the first two probes
                        last_search = True
                    if probe_action['action_type'] == 'SITREP' and action_taken['actionType'] == "Question" and action_taken['answer'] == 'Search':
                        # user answered search which matches action type of SITREP - match found
                        found_match = True
                        matched = probe_action
                        last_action_matched = ind
                        last_search = False
                        break
                    # check for vitals in sim
                    if (probe_action['action_type'] == 'CHECK_ALL_VITALS') and (action_taken['actionType'] in VITALS_ACTIONS) and self.do_characters_match(probe_action, action_taken):
                        found_match = True
                        matched = probe_action
                        last_action_matched = ind
                        break
                    # check for treatment
                    if (probe_action['action_type'] == 'APPLY_TREATMENT') and (action_taken['actionType'] == 'Treatment'):
                        # check specific treatment
                        char_match = self.do_characters_match(probe_action, action_taken)
                        treatment_match = 'parameters' not in probe_action or ('treatment' not in probe_action['parameters'] or (TREATMENT_MAP[probe_action['parameters']['treatment']] == action_taken['treatment']))
                        location_match = 'parameters' not in probe_action or ('location' not in probe_action['parameters']) or (action_taken['treatment'] in NO_LOCATION) or ('location' in probe_action['parameters'] and probe_action['parameters']['location'] == action_taken['treatmentLocation'].lower())
                        if char_match and treatment_match and location_match:
                            found_match = True
                            matched = probe_action
                            last_action_matched = ind
                            break
                        elif char_match and first_treatment:
                            found_match = True
                            matched = probe_action
                            break 
                        else:
                            # find close matches and rank by closest and earliest
                            tmp_count = char_match*3 + treatment_match*2 + location_match
                            # print(scene_ind, tmp_count, count_close, ind, close_ind, probe_action['character_id'], action_taken['casualty'])
                            # if (tmp_count == count_close and ind < close_ind) or tmp_count > count_close:
                            #     close_match = probe_action
                            #     action_for_close_match = action_taken  
                            #     count_close = tmp_count
                            #     close_ind = ind
                    # check for tagging - handle differently by searching through all actions to find the last tag given to this character
                    if (probe_action['action_type'] == 'TAG_CHARACTER'):
                        char_tag = self.find_last_tag_for_character(CHARACTER_MAP[probe_action['character_id']], self.json_data['actionList'])
                        if char_tag is None:
                            # no tag found!
                            self.logger.log(LogLevel.WARN, f"No tag given to {CHARACTER_MAP[probe_action['character_id']]}")
                            continue
                        # check specific tag to find perfectly matching probe
                        tag_match = 'parameters' not in probe_action or (('category' not in probe_action['parameters'] or  probe_action['parameters']['category'] == char_tag['tagType']))
                        if tag_match:
                            found_match = True
                            matched = probe_action
                            action_taken = char_tag
                            break
                        else:
                            close_match = probe_action
                            action_for_close_match = char_tag   
                if found_match:
                    print(f'found match for {scene_ind}') 
                    # matches_found += 1
                    second_attempt = False
                    # stay at the same action index if it is probe x.1, x.2, or x.3
                    if not last_search and not first_treatment:
                        action_list_start += last_action_matched
                    elif last_search:
                        last_search = False
                        first_treatment = True
                    elif first_treatment:
                        first_treatment = False

                    match_data.append({
                        "scene_index": scene_ind,
                        "probe_id": matched['probe_id'],
                        "found_match": True,
                        "probe": matched,
                        "user_action": action_taken
                    })
                    # reset variables
                    all_actions = []
                    all_probes = []
                    close_match = None
                    action_for_close_match = None
                    count_close = -1
                    close_ind = float('inf')
                    # set next scene
                    scene_ind = matched.get('next_scene', scene_ind + 1)
                    break

            # if we get out of the for loop without finding a match, we need to skip the scene
            if not found_match:
                print('skipping scene')
                scene_ind += 1
        # self.logger.log(LogLevel.CRITICAL_INFO, 'SoarTech matches found: ' + str(matches_found) + '/' + str(matches_found+len(skipped_scenes)))
        # self.logger.log(LogLevel.CRITICAL_INFO, 'SoarTech skipped sccenes: ' + str(skipped_scenes))
        json.dump(match_data, self.output_soartech, indent=4)
    
    # def check_soartech_probes_legacy(self):
    #     '''
    #     Looks through actions and attempts to match them with soartech probes
    #     '''
    #     print()
    #     self.logger.log(LogLevel.CRITICAL_INFO, "** SOARTECH **")
    #     soartech_scenes = self.soartech_yaml['scenes']
    #     scene_ind = 0
    #     found_all = False
    #     action_list_start = 0
    #     last_action_matched = 0
    #     second_attempt = False
    #     matches_found = 0
    #     skipped_scenes = []
    #     match_data = []
    #     last_search = False # was the last probe search/engage?
    #     first_treatment = False # are we now looking for the first treatment?

    #     while not found_all:
    #         if action_list_start > len(self.json_data['actionList']):
    #             break
    #         all_actions = []
    #         all_probes = []
    #         # in case we don't find a perfect match, keep track of close matches
    #         close_match = None
    #         action_for_close_match = None
    #         count_close = -1
    #         close_ind = float('inf') # so we can choose the earliest one with the highest match value
    #         for (ind, action_taken) in enumerate(self.json_data['actionList'][action_list_start:]):
    #             scene = self.get_scene_by_index(soartech_scenes, scene_ind)
    #             if scene is None:
    #                 found_all = True
    #                 break
    #             all_actions.append(action_taken['actionType'] + ' - ' + action_taken['casualty'])
    #             actions = scene["action_mapping"]
    #             found_match = False
    #             matched = None

    #             # see if it's the end of the simulation
    #             if 'end_scene_allowed' in scene and scene['end_scene_allowed']:
    #                 found_all = True
    #                 break
    #             # for each action the user took, see if it matches an action in the active scene
    #             for possible_action in actions:
    #                 str_act = possible_action['action_type'] + ' - ' + (possible_action['character_id'] if 'character_id' in possible_action else '')
    #                 if str_act not in all_probes:
    #                     all_probes.append(str_act)
    #                 # check for sim sitrep (when "search" is answered for a question)
    #                 if possible_action['action_type'] == 'SITREP':
    #                     last_search = True
    #                 if possible_action['action_type'] == 'SITREP' and action_taken['actionType'] == "Question" and action_taken['answer'] == 'Search':
    #                     found_match = True
    #                     matched = possible_action
    #                     last_action_matched = ind
    #                     last_search = False
    #                     break
    #                 # check for vitals in sim
    #                 if (possible_action['action_type'] == 'CHECK_ALL_VITALS') and (action_taken['actionType'] in VITALS_ACTIONS) and self.do_characters_match(possible_action, action_taken):
    #                     found_match = True
    #                     matched = possible_action
    #                     last_action_matched = ind
    #                     break
    #                 # check for treatment
    #                 if (possible_action['action_type'] == 'APPLY_TREATMENT') and (action_taken['actionType'] == 'Treatment'):
    #                     # check specific treatment
    #                     char_match = self.do_characters_match(possible_action, action_taken)
    #                     treatment_match = 'parameters' not in possible_action or ('parameters' in possible_action and ('treatment' not in possible_action['parameters'] or ('treatment' in possible_action['parameters'] and TREATMENT_MAP[possible_action['parameters']['treatment']] == action_taken['treatment'])))
    #                     location_match = 'parameters' not in possible_action or ('location' not in possible_action['parameters']) or (action_taken['treatment'] in NO_LOCATION) or ('location' in possible_action['parameters'] and possible_action['parameters']['location'] == action_taken['treatmentLocation'].lower())
    #                     if char_match and treatment_match and location_match:
    #                         found_match = True
    #                         matched = possible_action
    #                         last_action_matched = ind
    #                         break
    #                     else:
    #                         tmp_count = char_match*3 + treatment_match*2 + location_match
    #                         print(scene_ind, tmp_count, count_close, ind, close_ind, possible_action['character_id'], action_taken['casualty'])
    #                         if tmp_count == count_close and ind < close_ind:
    #                             close_match = possible_action
    #                             action_for_close_match = action_taken  
    #                             count_close = tmp_count
    #                             close_ind = ind
    #                         if tmp_count > count_close:
    #                             close_match = possible_action
    #                             action_for_close_match = action_taken  
    #                             count_close = tmp_count
    #                             close_ind = ind
    #                 # check for tagging - handle differently by searching through all actions to find the last tag given to this character
    #                 if (possible_action['action_type'] == 'TAG_CHARACTER'):
    #                     char_tag = self.find_last_tag_for_character(CHARACTER_MAP[possible_action['character_id']], self.json_data['actionList'])
    #                     if char_tag is None:
    #                         # no tag found!
    #                         self.logger.log(LogLevel.WARN, f"No tag given to {CHARACTER_MAP[possible_action['character_id']]}")
    #                         continue
    #                     # check specific tag
    #                     tag_match = 'parameters' not in possible_action or (('category' not in possible_action['parameters'] or ('category' in possible_action['parameters'] and possible_action['parameters']['category'] == char_tag['tagType'])))
    #                     if tag_match:
    #                         found_match = True
    #                         matched = possible_action
    #                         action_taken = char_tag
    #                         break
    #             # log matching data
    #             if found_match:
    #                 matches_found += 1
    #                 second_attempt = False
    #                 # stay at the same action index if it is probe x.1, x.2, or x.3
    #                 if not last_search or not first_treatment:
    #                     action_list_start += last_action_matched
    #                 elif last_search:
    #                     last_search = False
    #                     first_treatment = True
    #                 elif first_treatment:
    #                     first_treatment = False
    #                 all_actions = []
    #                 all_probes = []
    #                 close_match = None
    #                 action_for_close_match = None
    #                 count_close = -1
    #                 close_ind = float('inf')
    #                 match_data.append({
    #                     "scene_index": scene_ind,
    #                     "probe_id": matched['probe_id'],
    #                     "found_match": True,
    #                     "probe": matched,
    #                     "user_action": action_taken
    #                 })
    #                 # set next scene
    #                 if 'next_scene' in matched:
    #                     scene_ind = matched['next_scene']
    #                 else:
    #                     scene_ind += 1
    #         else:
    #             if second_attempt:
    #                 self.logger.log(LogLevel.WARN, f"Did not find any match for SoarTech probe at index {scene_ind}. Skipping scene...")
    #                 skipped_scenes.append(scene_ind)
    #                 match_data.append({
    #                     "scene_index": scene_ind,
    #                     "probe_id": close_match['probe_id'] if close_match is not None else 'None',
    #                     "found_match": False,
    #                     "probe": close_match,
    #                     "user_action": action_for_close_match,
    #                     "all_actions": all_actions,
    #                     "all_probes": all_probes
    #                 })
    #                 scene_ind += 1
    #                 second_attempt = False
    #                 close_match = None
    #                 action_for_close_match = None
    #                 count_close = -1
    #                 close_ind = float('inf')
    #             else:
    #                 second_attempt = True
    #     self.logger.log(LogLevel.CRITICAL_INFO, 'SoarTech matches found: ' + str(matches_found) + '/' + str(matches_found+len(skipped_scenes)))
    #     self.logger.log(LogLevel.CRITICAL_INFO, 'SoarTech skipped sccenes: ' + str(skipped_scenes))
    #     json.dump(match_data, self.output_soartech, indent=4)
    # def check_soartech_probes(self):
    #     '''
    #     Looks through all user actions and attempts to match them to soartech probes
    #     '''
    #     print()
    #     self.logger.log(LogLevel.CRITICAL_INFO, "** SOARTECH **")
    #     soartech_scenes = self.soartech_yaml['scenes'] # get all soartech scenes so we can get the probes
    #     scene_ind = 0 # the current scene index for accessing allowed/expected actions
    #     found_all = False # keep track of when we've reached the end of the scenes
    #     action_list_start = 0 # the index for looking at user actions
    #     last_action_matched = 0 # the index of the last user action we used to match a probe
    #     second_attempt = False # sometimes we need to backtrack and search once more for an action, but we only search through twice
    #     matches_found = 0 # count how many perfect matches we found
    #     skipped_scenes = [] # keep a record of which scenes we missed
    #     match_data = [] # the matches found, for writing to the json
    #     last_search = False # was the last probe search/engage?
    #     first_treatment = False # are we now looking for the first treatment?

    #     # continue searching for matches until scenes have been exhausted
    #     while not found_all:
    #         if action_list_start > len(self.json_data['actionList']):
    #             break
    #         # keep track of all actions taken and all probes allowed in case a match is not found
    #         all_user_actions = []
    #         all_probes = []
    #         # in case we don't find a perfect match, keep track of close matches (right action/character, wrong treatment/tag)
    #         close_match = None
    #         action_for_close_match = None
    #         count_close = -1
    #         close_ind = float('inf') # so we can choose the earliest one with the highest match value
    #         # iterate through all user actions starting after the last one matched to a probe
    #         for (ind, action_taken) in enumerate(self.json_data['actionList'][action_list_start:]):
    #             scene = self.get_scene_by_index(soartech_scenes, scene_ind)
    #             if scene is None or scene.get('end_scene_allowed', False):
    #                 found_all = True
    #                 break
    #             # log action taken in case no match is found
    #             all_user_actions.append(action_taken.get('actionType') + ' - ' + action_taken.get('casualty') + ' - ' + action_taken.get('treatment') + ' - ' + action_taken.get('tagType'))
    #             yaml_actions = scene["action_mapping"]
    #             found_match = False
    #             matched = None

    #             # for each action the user took, see if it matches an action in the active scene
    #             for possible_action in yaml_actions:
    #                 # log probe allowed in case no match is found
    #                 str_act = possible_action['action_type'] + ' - ' + possible_action.get('character_id', '') + ' - ' + str(possible_action.get('parameters', ''))
    #                 if str_act not in all_probes:
    #                     all_probes.append(str_act)
    #                 # check for sim sitrep (when "search" is answered for a question)
    #                 if possible_action['action_type'] == 'SITREP':
    #                     # if SITREP is a possible action, we are looking for search vs engage. If engage is chosen, we want to log the action for at least the first two probes
    #                     last_search = True
    #                 if possible_action['action_type'] == 'SITREP' and action_taken['actionType'] == "Question" and action_taken['answer'] == 'Search':
    #                     # user answered search which matches action type of SITREP - match found
    #                     found_match = True
    #                     matched = possible_action
    #                     last_action_matched = ind
    #                     last_search = False
    #                     break
    #                 # check for vitals in sim
    #                 if (possible_action['action_type'] == 'CHECK_ALL_VITALS') and (action_taken['actionType'] in VITALS_ACTIONS) and self.do_characters_match(possible_action, action_taken):
    #                     found_match = True
    #                     matched = possible_action
    #                     last_action_matched = ind
    #                     break
    #                 # check for treatment
    #                 if (possible_action['action_type'] == 'APPLY_TREATMENT') and (action_taken['actionType'] == 'Treatment'):
    #                     # check specific treatment
    #                     char_match = self.do_characters_match(possible_action, action_taken)
    #                     treatment_match = 'parameters' not in possible_action or ('treatment' not in possible_action['parameters'] or (TREATMENT_MAP[possible_action['parameters']['treatment']] == action_taken['treatment']))
    #                     location_match = 'parameters' not in possible_action or ('location' not in possible_action['parameters']) or (action_taken['treatment'] in NO_LOCATION) or ('location' in possible_action['parameters'] and possible_action['parameters']['location'] == action_taken['treatmentLocation'].lower())
    #                     if char_match and treatment_match and location_match:
    #                         found_match = True
    #                         matched = possible_action
    #                         last_action_matched = ind
    #                         break
    #                     else:
    #                         # find close matches and rank by closest and earliest
    #                         tmp_count = char_match*3 + treatment_match*2 + location_match
    #                         print(scene_ind, tmp_count, count_close, ind, close_ind, possible_action['character_id'], action_taken['casualty'])
    #                         if (tmp_count == count_close and ind < close_ind) or tmp_count > count_close:
    #                             close_match = possible_action
    #                             action_for_close_match = action_taken  
    #                             count_close = tmp_count
    #                             close_ind = ind
    #                 # check for tagging - handle differently by searching through all actions to find the last tag given to this character
    #                 if (possible_action['action_type'] == 'TAG_CHARACTER'):
    #                     char_tag = self.find_last_tag_for_character(CHARACTER_MAP[possible_action['character_id']], self.json_data['actionList'])
    #                     if char_tag is None:
    #                         # no tag found!
    #                         self.logger.log(LogLevel.WARN, f"No tag given to {CHARACTER_MAP[possible_action['character_id']]}")
    #                         continue
    #                     # check specific tag to find perfectly matching probe
    #                     tag_match = 'parameters' not in possible_action or (('category' not in possible_action['parameters'] or  possible_action['parameters']['category'] == char_tag['tagType']))
    #                     if tag_match:
    #                         found_match = True
    #                         matched = possible_action
    #                         action_taken = char_tag
    #                         break
    #                     else:
    #                         close_match = possible_action
    #                         action_for_close_match = char_tag 
                
    #             # log matching data
    #             if found_match:
    #                 matches_found += 1
    #                 second_attempt = False
    #                 # stay at the same action index if it is probe x.1, x.2, or x.3
    #                 if not last_search or not first_treatment:
    #                     action_list_start += last_action_matched
    #                 elif last_search:
    #                     last_search = False
    #                     first_treatment = True
    #                 elif first_treatment:
    #                     first_treatment = False
    #                 # reset variables
    #                 all_user_actions = []
    #                 all_probes = []
    #                 close_match = None
    #                 action_for_close_match = None
    #                 count_close = -1
    #                 close_ind = float('inf')
    #                 # add match data to array for json output
    #                 match_data.append({
    #                     "scene_index": scene_ind,
    #                     "probe_id": matched['probe_id'],
    #                     "found_match": True,
    #                     "probe": matched,
    #                     "user_action": action_taken
    #                 })
    #                 # set next scene
    #                 scene_ind = matched.get('next_scene', scene_ind + 1)



    def get_scene_by_index(self, scenes, index):
        '''
        In case yaml scenes are not in order, this will grab the correct
        scene based on the numeric index
        '''
        for scene in scenes:
            if scene["index"] == index:
                return scene
        return None


    def do_characters_match(self, possible_action, action_taken):
        return ('character_id' in possible_action) and (CHARACTER_MAP[possible_action['character_id']].lower() == action_taken['casualty'].lower())


    def find_last_tag_for_character(self, char_id, user_actions):
        '''
        Searches through all user actions to find the LAST time a character (with char_id) is tagged
        '''
        latest_found = None
        for a in user_actions:
            if a['actionType'] == 'Tag' and a['casualty'].lower() == char_id.lower():
                latest_found = a
        return latest_found


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ITM - Probe Matcher', usage='converter.py [-h] -y PATH -j PATH')

    parser.add_argument('-f', '--file', dest='json_path', type=str, help='The path to the json file to analyze for matching. Required.')
    args = parser.parse_args()
    if not args.json_path:
        print("JSON Path (-f) is required to run the analyzer.")
        exit(0)
    json_path = args.json_path
    matcher = ProbeMatcher(json_path)
    matcher.match_probes()