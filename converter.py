import yaml, argparse, json, random
from logger import LogLevel, Logger


SCENE_MAP = {
    "jungle": "sim-jungle",
    "desert": "sim-desert",
    "urban": "sim-urban-sanitized",
    "submarine": "sim-sub"
}

SUPPLY_MAP = {
    "Hemostatic gauze": "hemostaticGauzeCount",
    "Tourniquet": "tourniquetCount",
    "Pressure bandage": "pressureBandageCount",
    "Decompression Needle": "decompressionNeedleCount",
    "Nasopharyngeal airway": "nasopharyngealAirwayCount",
    "Pulse Oximeter": "pulseOximeterAvailable",
    "Pain Medications": "painMedsCount",
    "Splint": "splintCount",
    "Blood": "ivBloodCount",
    "IV Bag": "ivSalineCount"
}

MENTAL_STATUS_MAP = {
    "AGONY": "agony",
    "CALM": "calm",
    "CONFUSED": "unresponsive",
    "SHOCK": "unresponsive",
    "UPSET": "upset",
    "UNRESPONSIVE": "unresponsive"
}

BREATHING_MAP = {
    "NORMAL": "normal",
    "FAST": "fast",
    "RESTRICTED": "restricted",
    "NONE": "none"
}

PULSE_MAP = {
    "NONE": "none",
    "FAINT": "faint",
    "NORMAL": "normal",
    "FAST": "fast"
}

INJ_LOC_MAP = {
    "right forearm": "R Forearm",
    "left forearm": "L Forearm",
    "right calf": "R Calf",
    "left calf": "L Calf",
    "right thigh": "R Thigh",
    "left thigh": "L Thigh",
    "right stomach": "R Stomach",
    "left stomach": "L Stomach",
    "right bicep": "R Bicep",
    "left bicep": "L Bicep",
    "right shoulder": "R Shoulder",
    "left shoulder": "L Shoulder",
    "right side": "R Side",
    "left side": "L Side",
    "right chest": "R Chest",
    "left chest": "L Chest",
    "right wrist": "R Wrist",
    "left wrist": "L Wrist",
    "left face": "Face",
    "right face": "Face",
    "left neck": "L Neck",
    "right neck": "R Neck"
}

ALLOWED_INJURIES = [
    "Forehead Scrape",
    "Face Shrapnel",
    "Ear Bleed",
    "L Wrist Amputation",
    "R Wrist Amputation",
    "L Palm Laceration",
    "R Palm Laceration",
    "L Forearm Laceration",
    "R Forearm Laceration",
    "L Bicep Puncture",
    "L Shoulder Puncture",
    "R Shoulder Puncture",
    "R Bicep Puncture",
    "L Chest Collapse",
    "R Chest Collapse",
    "Asthmatic",
    "Hidden_StomachLaceration",
    "L Stomach Puncture",
    "R Stomach Puncture",
    "L Side Puncture",
    "R Side Puncture",
    "L Thigh Puncture",
    "R Thigh Puncture",
    "L Shin Amputation",
    "R Shin Amputation",
    "L Calf Laceration",
    "L Calf Shrapnel",
    "R Calf Shrapnel",
    "R Calf Laceration",
    "L Thigh Laceration",
    "L Neck Puncture",
    "R Neck Puncture",
    "Full Body Burn",
    "L Body Burn" ,
    "L Leg Broken",
    "R Leg Broken",
    "L Shoulder Broken",
    "R Shoulder Broken",
    "L Lower Leg Burn",
    "R Lower Leg Burn",
    "L Upper Leg Burn",
    "R Upper Leg Burn",
    "L Chest Burn",
    "R Chest Burn",
    "L Forearm Burn",
    "R Forearm Burn"
]

MALE_VOICES = ['Clyde_Male', 'Drew_Male', 'Giovanni_Male', 'Jami_Male', 'Julien_Male', 'Lev_Male', 'Michael_Male', 'Rashid_Male', 'Shaquille_Male', 'Vijay_Male']
FEMALE_VOICES = ['Alba_Female', 'Asmodia_Female', 'Diane_Female', 'Enni_Female', 'Gigi_Female', 'Grace_Female', 'Loredana_Female', 'Mampai_Female', 'Matilda_Female', 'Megan_Female']

MALE_NAMES = [
    'Adam',
    'Andrew',
    'Anthony',
    'Ben',
    'Brian',
    'Carlos',
    'Charles',
    'Christopher',
    'Daniel',
    'David',
    'Elijah',
    'Eric',
    'Francis',
    'Frank',
    'Gregory',
    'Ian',
    'Isaac',
    'James',
    'Jacob',
    'Jeff',
    'John',
    'Jose',
    'Juan',
    'Keith',
    'Kevin',
    'Larry',
    'Louis',
    'Marcus',
    'Mark',
    'Matthew',
    'Maurice',
    'Michael',
    'Nick',
    'Owen',
    'Patrick',
    'Paul',
    'Peter',
    'Phillip',
    'Ralph',
    'Richard',
    'Robert',
    'Ryan',
    'Scott',
    'Sean',
    'Steve',
    'Thomas',
    'Tim',
    'Todd',
    'Victor',
    'William'
]

FEMALE_NAMES = [
    'Abigail',
    'Allison',
    'Amanda',
    'Amy',
    'Angela',
    'Anna',
    'Ashley',
    'Brittany',
    'Christina',
    'Courtney',
    'Elizabeth',
    'Emily',
    'Emma',
    'Erin',
    'Grace',
    'Heather',
    'Hannah',
    'Jamie',
    'Jennifer',
    'Jessica',
    'Julie',
    'Karen',
    'Katherine',
    'Kelly',
    'Kimberly',
    'Laura',
    'Lauren',
    'Lisa',
    'Mary',
    'Megan',
    'Melissa',
    'Michelle',
    'Natalie',
    'Nicole',
    'Olivia',
    'Patricia',
    'Rachel',
    'Rebecca',
    'Samantha',
    'Sarah',
    'Shannon',
    'Stephanie',
    'Susan',
    'Taylor',
    'Teresa',
    'Tiffany',
    'Vanessa',
    'Victoria',
    'Wendy',
    'Zoe'
]

class YamlConverter:
    logger = Logger("yamlConverter")
    file = None
    loaded_yaml = None
    json_loc = ''

    def __init__(self, yaml_path, json_path):
        '''
        Load in the file and parse the yaml
        '''
        self.file = self.validate_file_location(yaml_path)
        try:
            self.loaded_yaml = yaml.load(self.file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, "Error while loading in yaml file. Please ensure the file is a valid yaml format and try again.\n\n" + str(e) + "\n")
        self.json_loc = json_path

    def __del__(self):
        '''
        Basic cleanup: closing the file loaded in on close.
        '''
        self.logger.log(LogLevel.DEBUG, "Program closing...")
        if (self.file):
            self.file.close()

    def validate_file_location(self, filename):
        '''
        Try to load in the yaml file. Checks that a path has been given, that the path leads to a yaml file,
        and that the file is found. Returns the open binary file object.
        '''
        if not filename:
            self.logger.log(LogLevel.ERROR, "No filename received. To run, please use 'python3 converter.py -f [filename]'")
        if not filename.strip().endswith('.yaml'):
            self.logger.log(LogLevel.ERROR, "File must be a yaml file.")
        try:
            f = open(filename, 'r')
            return f
        except:
            self.logger.log(LogLevel.ERROR, "Could not open file " + filename + ". Please make sure the path is valid and the file exists.")


    def convert_yaml_to_json(self):
        '''
        Converts a TA1 yaml file to a valid simulator json
        '''
        output = {}
        environment = self.loaded_yaml['state']['environment']
        
        # start by getting scene type
        output['scene'] = SCENE_MAP[environment['sim_environment']['type']]
        
        # create empty narrative (TODO - add some sections?)
        output['narrative'] = {
            "narrativeDescription": self.loaded_yaml['id'] + ' Narrative',
            "narrativeSections": []
        }

        # fill up scenarioData (no effect in sim)
        output['scenarioData'] = {
            "name": environment['sim_environment']['type'],
            "description": environment['decision_environment']['unstructured'],
            "difficulty": 5
        }

        # set player data (TODO - probably sim specific, will need to fill this out manually)
        output['playerData'] = {
            "startPosition": {
                "x": 0,
                "y": 0,
                "z": 0
            },
            "startAngle": 0
        }

        # set starting inventory
        output['availableInventory'] = {}
        start_supplies = self.loaded_yaml['state']['supplies']
        for supply in start_supplies:
            if supply['type'] in SUPPLY_MAP:
                if ('Pulse Ox' not in supply['type']):
                    output['availableInventory'][SUPPLY_MAP[supply['type']]] = supply['quantity']
                else:
                    output['availableInventory'][SUPPLY_MAP[supply['type']]] = supply['reusable'] or supply['quantity'] > 0

        # set questions (TODO - will probably stay blank, just marking this here to remember to revisit)
        output['questions'] = []

        # set patients
        patients = []
        # start with characters visible on start
        characters = self.loaded_yaml['state']['characters']
        for c in characters:
            patients.append(self.convert_patient_data(c, True))
        
        # now get the data from the rest of the scenes to throw in the narrative
        for scene in self.loaded_yaml['scenes']:
            if 'state' in scene and 'characters' in scene['state']:
                for c in scene['state']['characters']:
                    found = False
                    for p in patients:
                        if c['id'] == p['name']:
                            found = True
                            break
                    if not found:
                        patients.append(self.convert_patient_data(c, False))
            # TODO: start filling narrative with transitions from one scene to the next, hiding and revealing characters

        output['patientDataList'] = patients
        # load json into json file
        f = open(self.json_loc, 'w')
        json.dump(output, f, indent=4)
        f.close()


    def convert_patient_data(self, c, first_scene):
        '''
        Converts a character from the yaml to a patient in the json
        '''
        patient = {}
        patient['name'] = c['id']
        patient_type = self.get_patient_type(c['demographics']) # choose character based on demographic data
        patient['patient'] = patient_type
        patient['enabledOnStart'] = first_scene

        # TODO: see if there's a better way to set positions, maybe based on
        # the environment instead of manual?
        patient['positionAngle'] = {
            "position": {
                "x": 0,
                "y": 0,
                "z": 0
            },
            "angle": 0
        }

        # set vitals from yaml
        vitals = c['vitals']
        patient['vitals'] = {
            "pulse": PULSE_MAP[vitals['heart_rate']],
            "breath": BREATHING_MAP[vitals['breathing']],
            "hearing": "normal", # TODO: find hearing?
            "SpO2": "normal" if vitals['Spo2'] > 88 else "low" if vitals['Spo2'] > 0 else "none",
            "mood": MENTAL_STATUS_MAP[vitals['mental_status']]
        }

        # TODO: set from yaml??
        patient['triageStatus'] = {
            "triageLevel": "delayed",
            "sort": self.get_triage_sort(vitals)
        }

        # TODO: set pose from yaml??
        patient['animations'] = {
            'pose': 'supine',
            'side': 'left'
        }

        # set burn victim from yaml
        patient['overrides'] = {
            'burnVictim': self.is_burn_victim(c['injuries']) if 'injuries' in c else False,
            'injuriesControlPatientStates': False
        }

        # set injuries from yaml
        injuries = []
        if 'injuries' in c:
            for i in c['injuries']:
                inj = ''
                inj = self.convert_injury(i)
                if inj is not None:
                    injuries.append(inj)
        patient['injuries'] = injuries

        # set race ethnicity from yaml
        patient['raceEthnicity'] = {
            "preset": self.get_race(c['demographics']['race']),
            "skinEyeHairFromPreset": True,
            "hairOverride": True,
            "voice": random.choice(MALE_VOICES) if c['demographics']['sex'] == 'M' else random.choice(FEMALE_VOICES),
            "voicePitch": "normal",
            "firstName": random.choice(MALE_NAMES) if c['demographics']['sex'] == 'M' else random.choice(FEMALE_NAMES)
        }

        # set body basic defaults
        patient['body'] = {
            "bodyTexture": 0,
            "bodyNormalMap": 0,
            "bodyColor": "original",
            "bodyColorBrightness": "#808080",
            "hairTexture": random.choice([0, 1, 2]) if patient_type != 'Bob' and patient_type != 'Military Mike' else 0 if patient_type == 'Bob' else random.choice([0, 1]),
            "hairColor": "original", # TODO: Random hair colors?
            "eyeColor": "blue"
        }

        # set military gear and clothing from yaml
        if c['demographics']['military_disposition'] == 'Civilian':
            # get textures based on character!
            top = 0
            bottom = 0
            shoe = 0
            if patient_type == 'Helga' or patient_type == 'Gloria' or patient_type == 'Gary' or patient_type == 'Lily':
                top = random.choice(range(3))
                bottom = random.choice(range(3))
                shoe = random.choice(range(2)) if patient_type == 'Helga' or patient_type == 'Gary' else 0
            if patient_type == 'Bob':
                top = random.choice(range(7))
                bottom = random.choice(range(3))
                shoe = 0
            if patient_type == 'Military Mike':
                top = 6
                bottom = 6
                shoe = 2

            patient['clothing'] = {
                "topTexture": top,
                "bottomTexture": bottom,
                "shoeTexture": shoe,
                "topColor": random.choice(["original", self.get_random_color(), self.get_random_color(), self.get_random_color(), self.get_random_dark_color()]),
                "bottomColor": random.choice(["original", self.get_random_dark_color(), self.get_random_dark_color(), self.get_random_dark_color()]),
                "shoeColor": random.choice(["darkBrown", "black", "original", "dark", self.get_random_dark_color(), self.get_random_dark_color(), self.get_random_dark_color(), self.get_random_color()]),
                "topColorBrightness": random.choice(["#707070", "#808080", "#909090"]),
                "bottomColorBrightness": random.choice(["#707070", "#808080", "#909090"]),
                "topAlphaMask": -1,
                "bottomAlphaMask": -1
            }

            patient["militaryGear"] = {
                "headGear": [],
                "faceGear": [],
                "backGear": [],
                "chestGear": [],
                "beltGear": [],
                "legGear": [],
                "gunGear": []
            }
        else:
            # get textures based on character!
            top = 0
            bottom = 0
            shoe = 0
            lily_top = {'jungle': 5, 'submarine': 4, 'desert': 6, 'urban': 7}
            lily_bottom = {'jungle': 4, 'submarine': 3, 'desert': 5, 'urban': 6}
            mike_top = {'jungle': 0, 'submarine': 2, 'desert': 1, 'urban': 5}
            mike_bottom = {'jungle': 0, 'submarine': 2, 'desert': 1, 'urban': 5}
            if patient_type == 'Lily':
                top = lily_top[self.loaded_yaml['state']['environment']['sim_environment']['type']]
                bottom = lily_bottom[self.loaded_yaml['state']['environment']['sim_environment']['type']]
                shoe = -1
            if patient_type == 'Gary':
                # ONLY FOR SUB!!
                top = 4
                bottom = 4
                shoe = 2
            if patient_type == 'Military Mike':
                top = mike_top[self.loaded_yaml['state']['environment']['sim_environment']['type']]
                bottom = mike_bottom[self.loaded_yaml['state']['environment']['sim_environment']['type']]
                shoe = random.choice(range(1))

            patient['clothing'] = {
                "topTexture": top,
                "bottomTexture": bottom,
                "shoeTexture": shoe,
                "topColor": "original",
                "bottomColor": "original",
                "shoeColor": "original",
                "topColorBrightness": "#808080",
                "bottomColorBrightness": "#808080",
                "topAlphaMask": -1,
                "bottomAlphaMask": -1
            }
            # TODO: randomize military gear given to characters; maybe based on rank??
            patient["militaryGear"] = {
                "headGear": [],
                "faceGear": [],
                "backGear": [],
                "chestGear": [],
                "beltGear": [],
                "legGear": [],
                "gunGear": []
            }
        return patient


    def convert_injury(self, injury):
        '''
        Converts injury data from yaml to proper json format
        '''
        inj = ''
        loc = injury['location']
        name = injury['name']
        if loc in INJ_LOC_MAP:
            inj += loc + ' '
        inj += name if name != "Chest Collapse" else "Collapse"
        if inj not in ALLOWED_INJURIES:
            if name == "Broken Bone":
                if 'thigh' in loc or 'calf' in loc:
                    if 'left' in loc:
                        inj = 'L Leg Broken'
                    if 'right' in loc:
                        inj = 'R Leg Broken'
                elif 'side' in loc or 'wrist' in loc or 'neck' in loc or 'forearm' in loc:
                    if 'left' in loc:
                        inj = 'L Shoulder Broken'
                    if 'right' in loc:
                        inj = 'R Shoulder Broken'
            if name == "Shrapnel":
                if 'face' in loc:
                    inj = 'Face Shrapnel'
            if inj in ALLOWED_INJURIES:
                self.logger.log(LogLevel.WARN, "Replaced injury '" + loc + ' ' + name + "' with '" + inj + "'")
                return {"type": inj}
            else:
                self.logger.log(LogLevel.WARN, "Could not find match for injury: '" + inj + "'. Skipping...")
                return None
        return {"type": inj}


    def is_burn_victim(self, injuries):
        '''
        Returns if any burn injuries exist on the character
        '''
        for i in injuries:
            if i['name'] == 'Burn':
                return True
        return False


    def get_triage_sort(self, vitals):
        '''
        Calculates the triage sorting level based on vitals
        '''
        sort = 'walker'
        if not vitals['ambulatory']:
            sort = 'waver'
        if vitals['avpu'] == 'UNRESPONSIVE' or vitals['mental_status'] == "UNRESPONSIVE" or vitals['mental_status'] == "CONFUSED" or vitals['mental_status'] == "SHOCK":
            sort = 'still'
        return sort


    def get_race(self, race):
        '''
        Sets a random variation of the race of the individual based on the yaml defined race
        '''
        variations = {"White": ['White 1', 'White 2', 'White 3'],
            "Asian": ['Asian 1', 'Asian 2'],
            "Black": ['Black 1', 'Black 2'],
            "Hispanic": ['Hispanic'],
            "American Indian": ['American Indian'],
            "Pacific Islander": ['Pacific Islander']
        }
        return random.choice(variations[race])


    def get_random_color(self):
        '''
        Return a random hex color
        '''
        vals = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
        hex_color = '#'
        for _ in range(6):
            hex_color += random.choice(vals)
        return hex_color


    def get_random_dark_color(self):
        '''
        Return a random hex color
        '''
        dark_vals = ['0', '1', '2', '3', '4', '5', '6']
        vals = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
        hex_color = '#'
        for i in range(6):
            if i % 2 == 0:
                hex_color += random.choice(dark_vals)
            else:
                hex_color += random.choice(vals)
        return hex_color


    def get_patient_type(self, demographics):
        '''
        Given the demographics from the yaml file, determines which character
        should play the patient
        '''
        if demographics['sex'] == 'M':
            if demographics['military_disposition'] != 'Civilian':
                return 'Military Mike'
            else:
                if demographics['age'] < 40:
                    return random.choice(['Military Mike', 'Bob', 'Bob'])
                else:
                    return 'Gary'
        else:
            if demographics['military_disposition'] != 'Civilian':
                return 'Lily'
            else:
                if demographics['age'] < 30:
                    return random.choice(['Lily', 'Helga'])
                elif demographics['age'] < 40:
                    return random.choice(['Lily', 'Lily', 'Gloria'])
                else:
                    return 'Gloria'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ITM - YAML Converter to JSON', usage='converter.py [-h] -y PATH -j PATH')

    parser.add_argument('-y', '--yamlpath', dest='yaml_path', type=str, help='The path to the yaml file. Required.')
    parser.add_argument('-j', '--jsonpath', dest='json_path', type=str, help='The path to the json file to be created. Required.')
    args = parser.parse_args()
    if not args.yaml_path or not args.json_path:
        print("Yaml path (-y PATH) and json path (-j PATH) are required arguments to run the converter.")
        exit(0)
    yaml_path = args.yaml_path
    json_path = args.json_path
    converter = YamlConverter(yaml_path, json_path)
    converter.convert_yaml_to_json()
    converter.logger.log(LogLevel.CRITICAL_INFO, "Yaml successfully converted to JSON! Don't forget to: \n(1) update player starting position; \n(2) update character starting positions; \n(3) set/verify character poses; \n(4) set/verify triage levels; \n(5) complete narrative")
