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

SEVERITY_MAP = {
    "None": "minor",
    "Smallest": "minor",
    "Small": "moderate",
    "Medium": "substantial",
    "Large": "major",
    "Largest": "extreme"
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
        yaml_state = {}
        yaml_state['unstructured'] = 'TODO'
        sim_env = {'type': self.json_data['scene'].split('-')[1].replace('sub', 'submarine')}
        dec_env = {'unstructured': 'TODO'}
        
        yaml_state['environment'] = {'sim_environment': sim_env, 'decision_environment': dec_env}
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
            new_c['unstructured'] = f"Patient is in a {c['animations']['pose']} position."
            new_c['unstructured_postassess'] = new_c['unstructured'] + 'TODO'
            patient = c['patient']
            race = c['raceEthnicity']['preset']
            new_c['demographics'] = {
                'age': randint(25, 35) if patient in ['Helga', 'Bob', 'Lily', 'Military Mike'] else randint(45, 58),
                'sex': 'M' if patient in ['Gary', 'Military Mike', 'Bob'] else 'F',
                'race': race.split(' ')[0] if 'Islander' not in race and 'Indian' not in race else race
            }
            vitals = c['vitals']
            new_c['vitals'] = {
                'avpu': 'ALERT' if MENTAL_STATUS_MAP[vitals['mood']] != 'UNRESPONSIVE' else 'UNRESPONSIVE',
                'ambulatory': c['triageStatus']['sort'] == 'walker',
                'mental_status': MENTAL_STATUS_MAP[vitals['mood']],
                'breathing': BREATHING_MAP[vitals['breath']],
                'heart_rate': PULSE_MAP[vitals['pulse']],
                'spo2': 0 if vitals['SpO2'] == 'none' else 90 if vitals['SpO2'] == 'low' else 97
            }
            injuries = []
            for i in c['injuries']:
                split_name = i['type'].split(' ')
                severity = SEVERITY_MAP[i.get('bloodPool', 'None')]
                if severity == 'minor':
                    # no blood pool assigned, decide on our own
                    if 'Puncture' in i['type']:
                        severity = 'major'
                    if 'Ampuation' in i['type']:
                        severity = 'extreme'
                    if 'Laceration' in i['type'] or 'Abrasion' in i['type']:
                        severity = 'moderate' if 'Thigh' not in i['type'] else 'major'
                    if 'Shrapnel' in i['type']:
                        severity = 'major'
                    if 'Chest Collapse' in i['type']:
                        severity = 'extreme'
                    if 'Burn' in i['type']:
                        severity = 'major'
                    if 'Broken Bone' in i['type']:
                        severity = 'moderate'
                injury = {
                    'name': split_name[-1] if 'Broken' not in i['type'] else 'Broken Bone',
                    'location': INJ_LOC_MAP[(' ').join(split_name[:-1])],
                    'status': 'discoverable',
                    'severity': severity
                }
                injuries.append(injury)
            new_c['injuries'] = injuries
            yaml_characters.append(new_c)
        return yaml_characters


    def get_freeform_scenes(self):
        '''
        Add freeform scene actions
        '''
        scene = {}
        scene['id'] = 0
        scene['end_scene_allowed'] = True
        scene['restricted_actions'] = ['DIRECT_MOBILE_CHARACTERS', 'SEARCH', 'MOVE_TO_EVAC']
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
