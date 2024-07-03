import yaml, argparse, json
from random import randint
from logger import LogLevel, Logger

LOGGER = Logger('JsonConverter')

class Indenter(yaml.Dumper):
    ### Source: https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation#:~:text=class%20MyDumper(yaml.Dumper)%3A%0A%0A%20%20%20%20def%20increase_indent(self%2C%20flow%3DFalse%2C%20indentless%3DFalse)%3A%0A%20%20%20%20%20%20%20%20return%20super(MyDumper%2C%20self).increase_indent(flow%2C%20False)
    def increase_indent(self, flow=False, indentless=False):
        return super(Indenter, self).increase_indent(flow, False)

SUPPLY_MAP = {
    "hemostaticGauzeCount": "Hemostatic gauze",
    "tourniquetCount": "Tourniquet",
    "pressureBandageCount": "Pressure bandage",
    "decompressionNeedleCount": "Decompression Needle",
    "nasopharyngealAirwayCount": "Nasopharyngeal airway",
    "pulseOximeterAvailable": "Pulse Oximeter",
    "painMedsCount": "Pain Medications",
    "splintCount": "Splint",
    "ivBloodCount": "Blood",
    "ivSalineCount": "IV Bag",
    "burnDressingCount": "Burn Dressing",
    "epiPenCount": "Epi Pen",
    "chestSealCount": "Vented Chest Seal",
    "blanketCount": "Blanket",
    "lollipopCount": "Fentanyl Lollipop"
}

MENTAL_STATUS_MAP = {
    "agony": "AGONY",
    "calm": "CALM",
    "unresponsive": "UNRESPONSIVE",
    "dead": "UNRESPONSIVE",
    "upset": "UPSET"
}

BREATHING_MAP = {
    "normal": "NORMAL",
    "fast": "FAST",
    "restricted": "RESTRICTED",
    "none": "NONE",
    "collapsedLeft": "RESTRICTED",
    "collapsedRight": "RESTRICTED",
    "collapsedBoth": "RESTRICTED"
}

PULSE_MAP = {
    "none": "NONE",
    "faint": "FAINT",
    "normal": "NORMAL",
    "fast": "FAST"
}

INJ_LOC_MAP = {
    "R Forearm": "right forearm",
    "L Forearm": "left forearm",
    "R Calf": "right calf",
    "L Calf": "left calf",
    "R Thigh": "right thigh",
    "L Thigh": "left thigh",
    "R Stomach": "right stomach",
    "L Stomach": "left stomach",
    "R Bicep": "right bicep",
    "L Bicep": "left bicep",
    "R Shoulder": "right shoulder",
    "L Shoulder": "left shoulder",
    "R Side": "right side",
    "L Side": "left side",
    "R Chest": "right chest",
    "C Chest": "center chest",
    "L Chest": "left chest",
    "R Wrist": "right wrist",
    "L Wrist": "left wrist",
    "Face": "left face",
    "L Neck": "left neck",
    "R Neck": "right neck",
    "R Leg": "right leg",
    "L Leg": "left leg",
    "R Palm": "right hand",
    "L Palm": "left hand",
    "R Upper Leg": "right thigh",
    "L Upper Leg": "left thigh",
    "R Shin": "right calf",
    "L Shin": "left calf",
    "L Lower Leg": "left calf",
    "R Lower Leg": "right calf"
}

INJ_TYPE_MAP = {
    "Broken": "Broken Bone",
    "Collapse": "Chest Collapse"
}

ENV_MAP = {
    "desert": {
        'type': 'desert',
        'weather': 'clear',
        'lighting': 'bright',
        'visibility': 'excellent',
        'noise_peak': 'noisy',
        'temperature': 92,
        'fauna': 'normal'
    },
    "jungle": {
        'type': 'jungle',
        'terrain': 'jungle',
        'temperature': 88,
        'humidity': 90,
        'visibility': 'low',
        'flora': 'lush'
    },
    "submarine": {
        'type': 'submarine',
        'terrain': 'indoors',
        'visibility': 'low',
        'fauna': 'none',
        'flora': 'none'
    },
    "urban": {
        'type': 'urban',
        'terrain': 'urban',
        'lighting': 'normal',
        'visibility': 'moderate',
        'noise_ambient': 'noisy',
        'flora': 'none',
        'fauna': 'none'
    }
}

SEVERITY_MAP = {
    "None": "minor",
    "Smallest": "minor",
    "Small": "moderate",
    "Medium": "substantial",
    "Large": "major",
    "Largest": "extreme"
}

POSE_MAP = {
    "standing": "standing",
    "sittingGround": "sitting on the ground",
    "sittingChair": "sitting on a chair",
    "kneeling": "kneeling",
    "supine": "in a supine position",
    "recovery": "in a recovery position on the ground",
    "fetal": "in a fetal position on the ground",
    "prone": "in a prone position on the ground",
    "shooting": "actively shooting"
}

class JsonConverter:
    json_data = {}
    output_dest = None

    def __init__(self, input_path, output_path):
        f = None
        try:
            f = open(input_path, 'r', encoding='utf-8')
            self.json_data = json.load(f)
            f.close()
        except Exception as e:
            if f is not None:
                f.close()
            LOGGER.log(LogLevel.FATAL, "Error while loading in json file -- " + str(e))
        
        try:
            if output_path[-5:] != '.yaml':
                LOGGER.log(LogLevel.FATAL, "Error while setting up output location -- output must be a .yaml file")
            self.output_dest = open(output_path, 'w', encoding='utf-8')
        except Exception as e:
            LOGGER.log(LogLevel.FATAL, "Error while setting up output location -- " + str(e))


    def __del__(self):
        if self.output_dest is not None:
            self.output_dest.close()


    def convert(self):
        yaml_data = {}
        yaml_data['id'] = self.json_data['scenarioData']['name']
        yaml_data['name'] = self.json_data['scenarioData']['description']
        sim_env = ENV_MAP[self.json_data['scene'].split('-')[1].replace('sub', 'submarine')]
        yaml_state = {}
        unstructured = 'TODO'
        narrative_sections = self.json_data.get('narrative', {}).get('narrativeSections', [])
        for x in narrative_sections:
            if 'additionalInfo' in x:
                # get the first additional info available for unstructured text
                unstructured = x['additionalInfo']
                break
        if unstructured == 'TODO':
            unstructured = f"You are a medic in {'a' if sim_env['type'] != 'urban' else 'an'} {sim_env['type']} environment. Several members of your team {'and some civilians ' if sim_env['type'] != 'submarine' else ''}have been injured. Please treat these casualties."

        yaml_state['unstructured'] = unstructured
        
        
        yaml_state['environment'] = {'sim_environment': sim_env}
        yaml_state['supplies'] = self.get_supplies()
        yaml_state['characters'] = self.get_characters()
        yaml_data['state'] = yaml_state
        yaml_scenes = self.get_freeform_scenes()
        yaml_data['scenes'] = yaml_scenes
        yaml.dump(yaml_data, self.output_dest, allow_unicode=True, Dumper=Indenter, sort_keys=False, default_flow_style=False)
        LOGGER.log(LogLevel.CRITICAL_INFO, "Completed file conversion")


    def get_supplies(self):
        '''
        Returns a yaml-formatted object of supplies based on the json data
        '''
        inventory = self.json_data['availableInventory']
        supplies = []
        for item in inventory:
            supply = {"type": SUPPLY_MAP[item]}
            if type(inventory[item]) is int:
                supply['quantity'] = inventory[item]
            else:
                if inventory[item]:
                    supply["quantity"] = 1
                    supply['reusable'] = True
                else:
                    supply['quantity'] = 0 
            supplies.append(supply)
        return supplies
    

    def get_characters(self):
        '''
        Returns a yaml-formatted object of characters based on the json data
        '''
        characters = self.json_data['patientDataList']
        yaml_characters = []
        for c in characters:
            new_c = {}
            new_c['id'] = c['name']
            new_c['name'] = c['raceEthnicity']['firstName']
            new_c['unstructured'] = ""
            new_c['unstructured_postassess'] = ""
            patient = c['patient']
            race = c['raceEthnicity']['preset']

            demographics = {
                'age': randint(25, 35) if patient in ['Helga', 'Bob', 'Lily', 'Military Mike'] else randint(45, 58),
                'sex': 'M' if patient in ['Gary', 'Military Mike', 'Bob'] else 'F',
                'race': race.split(' ')[0] if 'Islander' not in race and 'Indian' not in race else race
            }

            is_military = False
            us_military = True
            for gear in c['militaryGear']:
                if len(c['militaryGear'][gear]) > 0:
                    is_military = True
                    break
            if c['clothing']['bottomColor'] != 'original' or c['clothing']['topColor'] != 'original':
                us_military = False

            if is_military:
                demographics['military_disposition'] = 'Allied US' if us_military else 'Allied'
                sim_env = self.json_data['scene'].split('-')[1].replace('sub', 'submarine')
                if sim_env != 'submarine':
                    demographics['role'] = 'Infantry'
                demographics['mission_importance'] = 'normal'
                if us_military:
                    demographics['military_branch'] = 'US Army' if sim_env in ['jungle', 'desert', 'urban'] else 'US Navy'
            
            new_c['demographics'] = demographics
            vitals = c['vitals']
            new_c['vitals'] = {
                'avpu': 'ALERT' if MENTAL_STATUS_MAP[vitals['mood']] != 'UNRESPONSIVE' else 'UNRESPONSIVE',
                'ambulatory': c['triageStatus']['sort'] == 'walker',
                'mental_status': MENTAL_STATUS_MAP[vitals['mood']],
                'breathing': BREATHING_MAP[vitals['breath']],
                'heart_rate': PULSE_MAP[vitals['pulse']],
                'spo2': 'NONE' if vitals['SpO2'] == 'none' else 'LOW' if vitals['SpO2'] == 'low' else 'NORMAL'
            }
            injuries = []
            written_injuries = {}
            for i in c['injuries']:
                if i['type'] == 'Asthmatic':
                    injury = {
                        'name': 'Asthmatic',
                        'location': "internal",
                        'status': 'hidden'
                    }
                    written_injuries[injury['name']] = ['internal']
                elif i['type'] == 'Ear Bleed':
                    injury = {
                        'name': 'Ear Bleed',
                        'location': "right face" if randint(1, 2) > 1 else "left face",
                        'status': 'discoverable'
                    }
                    written_injuries[injury['name']] = [injury['location']]
                else:
                    if i['type'] == 'Forehead Scrape':
                        injury = {
                            'name': "Laceration",
                            'location': "left face",
                            'status': 'discoverable'
                        } 
                    else:
                        split_name = i['type'].split(' ')
                        injury = {
                            'name': split_name[-1] if split_name[-1] not in INJ_TYPE_MAP else INJ_TYPE_MAP[split_name[-1]],
                            'location': INJ_LOC_MAP[(' ').join(split_name[:-1])],
                            'status': 'discoverable'
                        }
                    bloodPool = i.get('bloodPool', None)
                    if bloodPool is not None:
                        severity = SEVERITY_MAP[bloodPool]
                    elif 'Burn' in i['type']:
                        severity = 'major'

                    injury['severity'] = severity
                    
                    if injury['name'] in written_injuries:
                        written_injuries[injury['name']].append(injury['location'])
                    else:
                        written_injuries[injury['name']] = [injury['location']]
                injuries.append(injury)
            new_c['injuries'] = injuries
            if len(written_injuries) == 0:
                unstructured_inj = 'Has no known injuries.'
            else:
                unstructured_inj = "Has"
                pronoun = 'his' if demographics['sex'] == 'M' else 'her'
                is_asthmatic = False
                for inj_set in written_injuries:
                    if len(written_injuries[inj_set]) == 1:
                        if inj_set == 'Chest Collapse':
                            unstructured_inj += f" a collapsed {written_injuries[inj_set][0]},".lower()
                        elif inj_set == "Shrapnel":
                            unstructured_inj += f" shrapnel in {pronoun} {written_injuries[inj_set][0]},".lower()
                        elif inj_set == "Amputation":
                            unstructured_inj += f" an amputated {written_injuries[inj_set][0]},".lower()
                        elif inj_set == "Asthmatic":
                            is_asthmatic = True
                        elif inj_set == 'Ear Bleed':
                            unstructured_inj += f" blood coming out of {pronoun} {written_injuries[inj_set][0].split(' ')[0]} ear,"
                        else:
                            unstructured_inj += f" a {inj_set} on {pronoun} {written_injuries[inj_set][0]},".lower()
                            
                    else:
                        if inj_set == 'Chest Collapse':
                            unstructured_inj += f" a collapsed left and right chest,".lower()
                        if inj_set == 'Asthmatic':
                            is_asthmatic = True
                        else:
                            unstructured_inj += f" several {inj_set} injuries,".lower()
                if unstructured_inj != 'Has':
                    comma_separated = unstructured_inj.split(',')
                    if len(comma_separated) == 2:
                        unstructured_inj = comma_separated[0] + '.'
                    else:
                        unstructured_inj = ','.join(comma_separated[:-2]) + f'{", " if len(comma_separated) > 3 else " "}and' + comma_separated[-2] + '.'
                else:
                    unstructured_inj = ""
            new_c['unstructured'] += f"{'Male' if demographics['sex'] == 'M' else 'Female'}, about {demographics['age']} years old, {POSE_MAP[c['animations']['pose']]}." 
            if is_military:
                new_c['unstructured'] += f" Wearing a {'US' if us_military else 'local'} military uniform."
            new_c['unstructured_postassess'] += new_c['unstructured'] + " " + unstructured_inj
            if is_asthmatic:
                new_c['unstructured_postassess'] += " Patient is asthmatic."
            yaml_characters.append(new_c)
        return yaml_characters


    def get_freeform_scenes(self):
        '''
        Add freeform scene actions
        '''
        scene = {}
        scene['id'] = 0
        scene['end_scene_allowed'] = True
        scene['restricted_actions'] = ['DIRECT_MOBILE_CHARACTERS', 'SEARCH', 'MOVE_TO_EVAC', 'MESSAGE']
        actions = []

        # add sitrep action
        actions.append({
            'action_id': 'sitrep',
            'action_type': 'SITREP',
            'unstructured': 'Ask for a SITREP from all patients',
            'probe_id': 'action-probe',
            'choice': 'sitrep',
            'conditions': {'elapsed_time_gt': 30000000}
        })

        # add check vitals action
        actions.append({
            'action_id': 'check_vitals',
            'action_type': 'CHECK_ALL_VITALS',
            'unstructured': "Check a patient's vital signs",
            'probe_id': 'action-probe',
            'choice': 'check-all-vitals',
            'repeatable': True,
            'conditions': {'elapsed_time_gt': 30000000}
        })


        # add tagging and treating actions for all patients (repeatable)
        for c in self.json_data['patientDataList']:
            name = c['raceEthnicity']['firstName']
            tag_action = {
                'action_id': 'tag-' + name.lower(),
                'action_type': 'TAG_CHARACTER',
                'unstructured': 'Tag ' + name,
                'character_id': c['name'],
                'probe_id': 'tagging-probe',
                'choice': 'tag-' + name.lower(),
                'repeatable': True,
                'conditions': {'elapsed_time_gt': 30000000}
            }
            actions.append(tag_action)

            treat_action = {
                'action_id': 'treat-' + name.lower(),
                'action_type': 'APPLY_TREATMENT',
                'unstructured': 'Treat an injury on ' + name,
                'character_id': c['name'],
                'probe_id': 'action-probe',
                'choice': 'treat-' + name.lower(),
                'repeatable': True,
                'conditions': {'elapsed_time_gt': 30000000}
            }
            actions.append(treat_action)


        scene['action_mapping'] = actions
        scene['transitions'] = {'elapsed_time_gt': 30000000}
        return [scene]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ITM - JSON to YAML Converter')

    parser.add_argument('-i', '--input', dest='input_path', type=str, help='The path to the input json file. Required.')
    parser.add_argument('-o', '--output', dest='output_path', type=str, help='The path to the output yaml file. Required.')
    args = parser.parse_args()
    if not args.input_path:
        LOGGER.log(LogLevel.FATAL, "Input path (-i) of json file is required to run.")
    if not args.output_path:
        LOGGER.log(LogLevel.FATAL, "Output path (-o) to yaml file is required to run.")
    converter = JsonConverter(args.input_path, args.output_path)
    converter.convert()
