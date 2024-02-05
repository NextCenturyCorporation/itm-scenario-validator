'''
Takes in the api.yaml file from swagger and generates a new one that 
has only the required properties in it for validation.
Also generates a state_changes.yaml which defines which properties 
are allowed in Scenes/State
'''

import yaml, copy
from decouple import config
from logger import Logger, LogLevel

SWAGGER_YAML = config('SWAGGER_YAML')
NEW_API = config('API_YAML')
STATE_CHANGES = config('STATE_YAML')

class ApiGenerator:
    logger = Logger("apiGenerator")
    api_file = None
    api_yaml = None
    new_api_file = None
    new_state_file = None

    def __init__(self):
        '''
        Load in the files
        '''
        self.new_api_file = open(NEW_API, 'w')
        self.new_state_file = open(STATE_CHANGES, 'w')
        try:
            self.api_file = open(SWAGGER_YAML)
            self.api_yaml = yaml.load(self.api_file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, "Error while loading in api yaml. Please check the .env to make sure the location is correct and try again.\n\n" + str(e) + "\n")

    def __del__(self):
        '''
        Basic cleanup: closing the file loaded in on close.
        '''
        self.logger.log(LogLevel.DEBUG, "Program closing...")
        if (self.new_api_file):
            self.new_api_file.close()
        if (self.api_file):
            self.api_file.close()
        if (self.new_state_file):
            self.new_state_file.close()
    
    def update_general_api(self):
        '''
        Updates properties in the api.yaml file that don't match with
        what we expect during TA1's validation.
        '''
        new_api = copy.deepcopy(self.api_yaml)
        # validator requires Scenario/Scenes
        required_scenario = new_api['components']['schemas']['Scenario']['required']
        required_scenario.append('scenes')

        # validator requires all vitals properties to be specified
        required_vitals = new_api['components']['schemas']['Vitals']['required'] if 'required' in new_api['components']['schemas']['Vitals'] else []
        required_vitals.append('conscious')
        required_vitals.append('avpu')
        required_vitals.append('mental_status')
        required_vitals.append('breathing')
        required_vitals.append('heart_rate')
        required_vitals.append('Spo2')
        new_api['components']['schemas']['Vitals']['required'] = required_vitals

        # injury status enum should only include hidden, discoverable, or visible
        new_api['components']['schemas']['InjuryStatusEnum']['enum'] = ['hidden', 'discoverable', 'visible']

        # create a new enum for restricted_actions that doesn't include END_SCENE
        new_api['components']['schemas']['RestrictedActionsEnum'] = copy.deepcopy(new_api['components']['schemas']['ActionTypeEnum'])
        new_api['components']['schemas']['RestrictedActionsEnum']['enum'].remove('END_SCENE')

        # set restricted_actions to this enum
        new_api['components']['schemas']['Scene']['properties']['restricted_actions']['items']['$ref'] = "#/components/schemas/RestrictedActionsEnum"

        # validator does not allow visited in character
        try:
            if 'visited' in new_api['components']['schemas']['Character']['required']:
                new_api['components']['schemas']['Character']['required'].remove('visited')
            del new_api['components']['schemas']['Character']['properties']['visited']
        except: 
            self.logger.log(LogLevel.INFO, "No 'visited' property found in 'Character'. Not removing anything")

        # validator does not allow session complete in scenario
        try:
            if 'session_complete' in required_scenario:
                required_scenario.remove('session_complete')
            del new_api['components']['schemas']['Scenario']['properties']['session_complete']
        except: 
            self.logger.log(LogLevel.INFO, "No 'session_complete' property found in 'Scenario'. Not removing anything")

        # validator does not allow scenario complete in state
        required_state = new_api['components']['schemas']['State']['required']
        try:
            if 'scenario_complete' in required_state:
                required_state.remove('scenario_complete')
            del new_api['components']['schemas']['State']['properties']['scenario_complete']
        except: 
            self.logger.log(LogLevel.INFO, "No 'scenario_complete' property found in 'State'. Not removing anything")

        # validator does not allow elapsed time in state
        try:
            if 'elapsed_time' in required_state:
                required_state.remove('elapsed_time')
            del new_api['components']['schemas']['State']['properties']['elapsed_time']
        except: 
            self.logger.log(LogLevel.INFO, "No 'elapsed_time' property found in 'State'. Not removing anything")
        return new_api
    

    def generate_new_api(self):
        '''
        Takes the current api.yaml and updates the properties whose required attributes 
        do not match between the validator and the api. Keeps the original api intact.
        '''
        new_api = self.update_general_api()
        # put the updated data into the yaml file
        yaml.dump(new_api, self.new_api_file, allow_unicode=True)
        self.logger.log(LogLevel.INFO, "Updated validator yaml. Find it at " + NEW_API)


    def generate_state_change_api(self):
        '''
        Takes the current api.yaml and pulls out only the state properties.
        Changes the requirements to match what is expected for state changes.
        '''
        updated_api = self.update_general_api()
        new_api = {'components': {'schemas': {}}}
        state_type = updated_api['components']['schemas']['State']
        new_api['components']['schemas']['State'] = state_type
        # go through everything required in state and grab it to put in the new api
        new_api['components']['schemas'].update(self.get_required_schemas(state_type, updated_api))

        # update the api to not require everything
        # state should only require characters; at least one unstructured will be required manually
        new_api['components']['schemas']['State']['required'] = ['characters']

        # mission only needs to require unstructured
        new_api['components']['schemas']['Mission']['required'] = ['unstructured']

        # environment can be empty
        del new_api['components']['schemas']['Environment']['required']

        # decision environment must have unstructured
        new_api['components']['schemas']['DecisionEnvironment']['required'] = ['unstructured']

        # sim environment must have unstructured
        new_api['components']['schemas']['SimEnvironment']['required'] = ['unstructured']

        # sim environment does not have type
        del new_api['components']['schemas']['SimEnvironment']['properties']['type']

        # aid delay can be empty, but id is still required
        new_api['components']['schemas']['AidDelay']['required'] = ['id']

        # put the updated data into the yaml file
        yaml.dump(new_api, self.new_state_file, allow_unicode=True)
        
        self.logger.log(LogLevel.INFO, "Updated state change yaml. Find it at " + STATE_CHANGES)



    def get_required_schemas(self, schema, full_api):
        '''
        Recursively looks through the properties of a schema and finds all other schemas
        required to fill out those properties
        '''
        required_schemas = {}
        properties = schema['properties'] if 'properties' in schema else []
        for k in properties:
            loc = None
            if "$ref" in properties[k]:
                loc = properties[k]["$ref"] 
            elif "items" in properties[k] and "$ref" in properties[k]['items']:
                loc = properties[k]["items"]["$ref"]
            if loc:
                loc = loc.split('/')[1:]
                data = full_api
                for x in loc:
                    data = data[x]
                required_schemas[loc[len(loc)-1]] = data
                required_schemas.update(self.get_required_schemas(data, full_api))
        return required_schemas

