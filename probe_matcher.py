import yaml, argparse, json, os, csv
from logger import LogLevel, Logger
from pymongo import MongoClient

SEND_TO_MONGO = True
EVAL_NUM = 3
EVAL_NAME = 'Metrics Evaluation'

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
    "casualty_w": "patient X",
    "casualty_x": "patient W",
    "patient_2_victim": "Adept Victim",
    "patient_1_shooter": "Adept Shooter",
    "electricians_mate": "electrician",
    "sailor_1": "bystander",
    "local_soldier_1": "Local Soldier 1",
    "us_soldier_1": "US Soldier 1",
    "civilian_1": "Civilian 1",
    "civilian_2": "Civilian 2"

}

TREATMENT_MAP = {
    "Nasopharyngeal airway": "Nasal Trumpet",
    "Pain Medications": "Pain Meds",
    "Splint": "Splint",
    "Blood": "IV - Blood",
    "IV Bag": "IV - Saline",
    "Burn Dressing": "Burn Dressing",
    "Vented Chest Seal": "Vented Chest Seal",
    "Decompression Needle": "Decompression Needle",
    "Pressure bandage": "Gauze Dressing",
    "Tourniquet": "Tourniquet",
    "Hemostatic gauze": "Hemostatic Gauze"
}

QA_MAP = {
    "Electrician": "electrician",
    "Bystander": "bystander",
    "Go": "sailor_2",
    "Stay": "sailor_1", # could be sailor 1 or electricians mate, but kdma is same
    "Patient 1/Shooter": "Adept Shooter",
    "Patient 2/Victim": "Adept Victim",
    "US Soldier": "us_soldier_1",
    "Local Soldier": "local_soldier_1",
    "Patient 1: Burn/Puncture": "Civilian 1",
    "Patient 2: Broken Bone": "Civilian 2"
}


VITALS_ACTIONS = ["SpO2", "Breathing", "Pulse"]
NO_LOCATION = ["Pain Meds", "IV - Blood", "IV - Saline", "Nasal Trumpet", "Decompression Needle", "Splint"]

mongo_collection_matches = None
mongo_collection_raw = None
ENVIRONMENTS_BY_PID = {}

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
    participantId = ''
    environment = ''
    csv_file = None

    def __init__(self, json_path, csv_path):
        '''
        Load in the file and parse the yaml
        '''
        # get environment from json to choose correct adept/soartech yamls
        self.json_file = open(json_path, 'r')
        self.json_data = json.load(self.json_file)
        if (self.json_data['configData']['teleportPointOverride'] == 'Tutorial'):
            self.logger.log(LogLevel.CRITICAL_INFO, "Tutorial level, not processing data")
            return
        if (len(self.json_data['actionList']) <= 1):
            self.logger.log(LogLevel.WARN, "No actions taken")
            return
        self.csv_file = open(csv_path, 'r')
        pid = self.json_data['participantId']
        pid = pid if pid != '' else self.json_data['sessionId']
        self.participantId = pid
        env = SCENE_MAP.get(self.json_data["configData"]["scene"], '')
        if env == '':
            self.logger.log(LogLevel.WARN, "Environment not defined. Unable to process data")
            return
        self.environment = env
        mongo_collection_raw.insert_one({'evalNumber': EVAL_NUM, 'evalName': EVAL_NAME, 'data': self.json_data, 'pid': self.participantId, '_id': self.participantId + '_' + self.environment})

        if pid in ENVIRONMENTS_BY_PID:
            ENVIRONMENTS_BY_PID[pid].append(self.environment)
        else:
            ENVIRONMENTS_BY_PID[pid] = [self.environment]
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
        if (self.csv_file):
            self.csv_file.close()


    def match_probes(self):
        self.logger.log(LogLevel.CRITICAL_INFO, f"Finding matches for {self.environment} environment")
        # adept first
        self.check_adept_probes()

        # analyze soartech probes
        self.check_soartech_probes()


    def check_adept_probes(self):
        '''
        Looks through actions and attempts to match them with adept probes
        '''
        print()
        self.logger.log(LogLevel.CRITICAL_INFO, "** ADEPT **")
        if 'jungle' in self.environment:
            self.check_adept_urban_jungle()
        if 'urban' in self.environment:
            self.check_adept_urban_jungle()
        if 'desert' in self.environment:
            self.check_adept_desert()
        if 'sub' in self.environment:
            self.check_adept_sub()


    def check_adept_urban_jungle(self):
        '''
        Finds actions matching to adept urban probes or jungle probes
        '''
        adept_scenes = self.adept_yaml['scenes']
        finished = False
        action_list_start = 0
        if 'jungle' in self.environment:
            chars = ["Civilian 1", "Civilian 2"]
        else:
            chars = ["Adept Victim", "Adept Shooter"]
        probe_id = 0
        match_data = []
        scene_ind = 0
        while not finished:
            scene = self.get_scene_by_index(adept_scenes, scene_ind)
            if scene is None or scene.get('end_scene_allowed', False):
                finished = True
                break
            found_match = False
            probe_found = None
            action_found = None
            for (ind, action_taken) in enumerate(self.json_data['actionList'][action_list_start:]): 
                # first probe - who is the first action performed on?
                if probe_id == 0:
                    # search through csv to find who was approached first
                    reader = csv.reader(self.csv_file)
                    for line in reader:
                        if 'PATIENT_ENGAGED' in line:
                            for c in chars:
                                if c + ' Root' in line:
                                    for probe_action in scene['action_mapping']:
                                        if c == CHARACTER_MAP[probe_action.get('character_id')]:
                                            found_match = True
                                            probe_id += 1
                                            probe_found = probe_action
                                            action_found = "Approached " + c
                                            break
                                if found_match:
                                    break
                            if found_match:
                                break
                    if not found_match:
                        if action_taken['casualty'] in chars:
                            # iterate through available actions to find matching character
                            for probe_action in scene['action_mapping']:
                                if self.do_characters_match(probe_action, action_taken):
                                    found_match = True
                                    probe_id += 1
                                    probe_found = probe_action
                                    action_found = action_taken
                                    action_list_start += ind
                                    break
                            if found_match:
                                break
                    else:
                        break
                elif probe_id == 1 and action_taken['casualty'] in chars and action_taken['actionType'] == 'Treatment':
                    # second probe - who do they apply a treatment to first?
                    # iterate through available actions to find matching character
                    for probe_action in scene['action_mapping']:
                        if self.do_characters_match(probe_action, action_taken):
                            found_match = True
                            probe_id += 1
                            probe_found = probe_action
                            action_found = action_taken
                            action_list_start += ind
                            break
                    if found_match:
                        break
                elif probe_id == 2 and action_taken['actionType'] == 'Question':
                    # third probe - answer to question: who to evac
                    for probe_action in scene['action_mapping']:
                        if CHARACTER_MAP[probe_action.get('character_id')] == QA_MAP[action_taken['answer']]:
                            found_match = True
                            probe_id += 1
                            probe_found = probe_action
                            action_found = action_taken
                            action_list_start += ind
                            break
                    if found_match: 
                        break

            if found_match:
                match_data.append({
                    "scene_index": scene_ind,
                    "probe_id": probe_found['probe_id'],
                    "found_match": True,
                    "probe": probe_found,
                    "user_action": action_found
                })
                scene_ind = probe_found.get('next_scene', scene_ind + 1)
            else:
                self.logger.log(LogLevel.WARN, f'No match found for scene {scene_ind}')
                scene_ind += 1
        if SEND_TO_MONGO:
            mongo_collection_matches.insert_one({'evalNumber': EVAL_NUM, 'evalName': EVAL_NAME, 'data': match_data, 'ta1': 'ad', 'env': self.environment.split('.yaml')[0], 'pid': self.participantId, '_id': self.participantId + '_ad_' + self.environment.split('.yaml')[0]})
        json.dump(match_data, self.output_adept, indent=4)      


    def check_adept_sub(self):
        '''
        Finds actions matching to adept submarine probes
        '''
        adept_scenes = self.adept_yaml['scenes']
        finished = False
        action_list_start = 0
        probe_id = 0
        match_data = []
        scene_ind = 0
        while not finished:
            scene = self.get_scene_by_index(adept_scenes, scene_ind)
            if scene is None or scene.get('end_scene_allowed', False):
                finished = True
                break
            found_match = False
            probe_found = None
            action_found = None
            for (ind, action_taken) in enumerate(self.json_data['actionList'][action_list_start:]): 
                # first probe - answer to question - who to treat first
                if probe_id == 0 and action_taken['actionType'] == 'Question' and 'Adept Probe: 1' in action_taken['question']:
                    for probe_action in scene['action_mapping']:
                        if CHARACTER_MAP[probe_action.get('character_id')] == QA_MAP[action_taken['answer']]:
                            found_match = True
                            probe_id += 1
                            probe_found = probe_action
                            action_found = action_taken
                            action_list_start += ind
                            break
                    if found_match:
                        break
                elif probe_id == 1 and action_taken['actionType'] == 'Treatment':
                    # second probe - who is treated first
                    for probe_action in scene['action_mapping']:
                        if self.do_characters_match(probe_action, action_taken):
                            found_match = True
                            probe_id += 1
                            probe_found = probe_action
                            action_found = action_taken
                            action_list_start += ind
                            break
                    if found_match:
                        break
                elif probe_id == 2 and action_taken['actionType'] == 'Question' and 'Adept Probe: 2' in action_taken['question']:
                    for probe_action in scene['action_mapping']:
                        if probe_action.get('character_id') == QA_MAP[action_taken['answer']]:
                            found_match = True
                            probe_id += 1
                            probe_found = probe_action
                            action_found = action_taken
                            action_list_start += ind
                            break
                    if found_match:
                        break        

            if found_match:
                match_data.append({
                    "scene_index": scene_ind,
                    "probe_id": probe_found['probe_id'],
                    "found_match": True,
                    "probe": probe_found,
                    "user_action": action_found
                })
                scene_ind = probe_found.get('next_scene', scene_ind + 1)
            else:
                self.logger.log(LogLevel.WARN, f'No match found for scene {scene_ind}')
                scene_ind += 1
        if SEND_TO_MONGO:
            mongo_collection_matches.insert_one({'evalNumber': EVAL_NUM, 'evalName': EVAL_NAME, 'data': match_data, 'ta1': 'ad', 'env': self.environment.split('.yaml')[0], 'pid': self.participantId, '_id': self.participantId + '_ad_' + self.environment.split('.yaml')[0]})
        json.dump(match_data, self.output_adept, indent=4)      


    def check_adept_desert(self):
        '''
        Finds actions matching to adept desert probes
        '''
        adept_scenes = self.adept_yaml['scenes']
        finished = False
        action_list_start = 0
        probe_id = 0
        match_data = []
        scene_ind = 0
        while not finished:
            scene = self.get_scene_by_index(adept_scenes, scene_ind)
            if scene is None or scene.get('end_scene_allowed', False):
                finished = True
                break
            found_match = False
            probe_found = None
            action_found = None
            for (ind, action_taken) in enumerate(self.json_data['actionList'][action_list_start:]): 
                # first probe - question from helicopter, who to evac
                first_probe = probe_id == 0 and action_taken['actionType'] == 'Question' and 'Adept Probe 1' in action_taken['question']
                # second probe - question from ground, who to evac
                second_probe = probe_id == 1 and action_taken['actionType'] == 'Question' and 'Adept Probe 2' in action_taken['question']
                # third probe - after treatment/final inject, who to evac
                third_probe = probe_id == 2 and action_taken['actionType'] == 'Question' and 'Adept Probe 3' in action_taken['question']
                if first_probe or second_probe or third_probe:
                    for probe_action in scene['action_mapping']:
                        if probe_action.get('character_id') == QA_MAP[action_taken['answer']]:
                            found_match = True
                            probe_id += 1
                            probe_found = probe_action
                            action_found = action_taken
                            action_list_start += ind
                            break
                    if found_match:
                        break
            if found_match:
                match_data.append({
                    "scene_index": scene_ind,
                    "probe_id": probe_found['probe_id'],
                    "found_match": True,
                    "probe": probe_found,
                    "user_action": action_found
                })
                scene_ind = probe_found.get('next_scene', scene_ind + 1)
            else:
                self.logger.log(LogLevel.WARN, f'No match found for scene {scene_ind}')
                scene_ind += 1
        if SEND_TO_MONGO:
            mongo_collection_matches.insert_one({'evalNumber': EVAL_NUM, 'evalName': EVAL_NAME, 'data': match_data, 'ta1': 'ad', 'env': self.environment.split('.yaml')[0], 'pid': self.participantId, '_id': self.participantId + '_ad_' + self.environment.split('.yaml')[0]})
        json.dump(match_data, self.output_adept, indent=4)  


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
            if scene is None or scene.get('end_scene_allowed', False) or action_list_start > len(self.json_data['actionList']):
                found_all = True
                break
            # iterate through all user actions taken
            found_match = False
            no_tag = False
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
                    if (probe_action['action_type']) == 'CHECK_PULSE' and action_taken['actionType'] == "Pulse" and self.do_characters_match(probe_action, action_taken):
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
                    # check for tagging - handle differently by searching through all actions to find the last tag given to this character
                    if (probe_action['action_type'] == 'TAG_CHARACTER'):
                        char_tag = self.find_last_tag_for_character(CHARACTER_MAP[probe_action['character_id']], self.json_data['actionList'])
                        if char_tag is None and not no_tag:
                            # no tag found!
                            self.logger.log(LogLevel.WARN, f"No tag given to {CHARACTER_MAP[probe_action['character_id']]}")
                            no_tag = True
                            continue
                        elif no_tag:
                            continue
                        # check specific tag to find perfectly matching probe
                        tag_match = 'parameters' not in probe_action or (('category' not in probe_action['parameters'] or  probe_action['parameters']['category'] == char_tag['tagType']))
                        if tag_match:
                            found_match = True
                            matched = probe_action
                            action_taken = char_tag
                            break 
                if found_match:
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
                    last_action_matched = 0
                    # set next scene
                    scene_ind = matched.get('next_scene', scene_ind + 1)
                    break
                elif no_tag:
                    match_data.append({
                        "scene_index": scene_ind,
                        "probe_id": None,
                        "found_match": False,
                        "probe": None,
                        "user_action": "No tag given"
                    })
                    scene_ind += 1
                    break

            # if we get out of the for loop without finding a match, we need to skip the scene
            if not found_match and not found_all:
                # find the closest match we can out of ALL actions - order no longer matters
                close_count = -1
                close_ind = -1
                close_probe = None
                close_action = None
                i = 0
                for action_taken in self.json_data['actionList']:  
                    for probe_action in scene['action_mapping']:
                        if self.do_characters_match(probe_action, action_taken) and (probe_action['action_type'] == 'APPLY_TREATMENT') and (action_taken['actionType'] == 'Treatment'):
                            treatment_match = 'parameters' not in probe_action or ('treatment' not in probe_action['parameters'] or (TREATMENT_MAP[probe_action['parameters']['treatment']] == action_taken['treatment']))
                            location_match = 'parameters' not in probe_action or ('location' not in probe_action['parameters']) or (action_taken['treatment'] in NO_LOCATION) or ('location' in probe_action['parameters'] and probe_action['parameters']['location'] == action_taken['treatmentLocation'].lower())
                            tmp_count = treatment_match*3 + location_match
                            if tmp_count > close_count or (tmp_count == close_count and abs(action_list_start-i) < abs(action_list_start-close_ind)):
                                close_ind = i
                                close_count = tmp_count
                                close_probe = probe_action
                                close_action = action_taken
                    i += 1
                if close_count == -1:
                    self.logger.log(LogLevel.WARN, f'No match found for scene {scene_ind}')
                    match_data.append({
                        "scene_index": scene_ind,
                        "found_match": False,
                    })
                    scene_ind += 1
                else:
                    self.logger.log(LogLevel.DEBUG, f'Imperfect match found for scene {scene_ind}')
                    match_data.append({
                        "scene_index": scene_ind,
                        "probe_id": close_probe['probe_id'],
                        "found_match": False,
                        "probe": close_probe,
                        "user_action": close_action
                    })
                    scene_ind = close_probe.get('next_scene', scene_ind + 1)
        if SEND_TO_MONGO:
            mongo_collection_matches.insert_one({'evalNumber': EVAL_NUM, 'evalName': EVAL_NAME, 'data': match_data, 'ta1': 'st', 'env': self.environment.split('.yaml')[0], 'pid': self.participantId, '_id': self.participantId + '_st_' + self.environment.split('.yaml')[0]})
        json.dump(match_data, self.output_soartech, indent=4)


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
    parser = argparse.ArgumentParser(description='ITM - Probe Matcher', usage='probe_matcher.py [-h] -i PATH')

    parser.add_argument('-i', '--input_dir', dest='input_dir', type=str, help='The path to the directory where all participant files are. Required.')
    args = parser.parse_args()
    if not args.input_dir:
        print("Input directory (-i PATH) is required to run the probe matcher.")
        exit(1)
    if SEND_TO_MONGO:
        # instantiate mongo client
        client = MongoClient("mongodb://simplemongousername:simplemongopassword@localhost:27017/?authSource=dashboard")
        db = client.dashboard
        # create new collection for simulation runs
        mongo_collection_matches = db['humanSimulator']
        mongo_collection_raw = db['humanSimulatorRaw']
    # dirs = ['metrics-data/json/json', 'metrics-data/json', 'metrics-data/unknown json id']
    # for d in dirs:
    #     for x in os.listdir(d):
    #         if not os.path.isdir(os.path.join(d, x)):
    #             try:
    #                 os.mkdir(f'metrics-data/{x.split(".json")[0]}')
    #                 os.mkdir(f'metrics-data/{x.split(".json")[0]}/{x.split(".json")[0]}')
    #                 os.system(f'mv {os.path.join(d, x)} metrics-data/{x.split(".json")[0]}/{x.split(".json")[0]}/{x}')
    #             except:
    #                 pass
    # go through the input directory and find all sub directories
    sub_dirs = [name for name in os.listdir(args.input_dir) if os.path.isdir(os.path.join(args.input_dir, name))]
    # for each subdirectory, see if a json file exists
    for dir in sub_dirs:
        grandparent = os.path.join(args.input_dir, dir)
        for d in os.listdir(grandparent):
            parent = os.path.join(grandparent, d)
            if os.path.isdir(parent):
                for f in os.listdir(parent):
                    if '.json' in f:
                        print(f"\n** Processing {f} **")
                        # json found! grab matching csv and send to the probe matcher
                        try:
                            matcher = ProbeMatcher(os.path.join(parent, f), os.path.join(args.input_dir, dir.split('_')[0] + '_.csv'))
                            if matcher.environment != '':
                                matcher.match_probes()
                            break
                        except:
                            pass
    print(json.dumps(ENVIRONMENTS_BY_PID, indent=4))
