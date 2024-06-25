import yaml, argparse, json, copy
from api_files.generator import ApiGenerator
from logger import LogLevel, Logger
from decouple import config

API_YAML = config('API_YAML')
STATE_YAML = config('STATE_YAML')
DEP_JSON = config('DEP_JSON')

# special loader with duplicate key checking (https://gist.github.com/pypt/94d747fe5180851196eb)
class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"Duplicate key {key!r} found in YAML.")
            mapping.append(key)
        return super().construct_mapping(node, deep)


PRIMITIVE_TYPE_MAP = {
    'string': str,
    'boolean': bool,
    'number': float,
    'int': int,
    'integer': int
}
# state in scene should follow state_changes.yaml

class YamlValidator:
    logger = Logger("yamlValidator")
    file = None
    dup_check_file = None
    api_file = None
    dep_file = None
    state_change_file = None
    loaded_yaml = None
    api_yaml = None
    state_changes_yaml = None
    dep_json = None
    missing_keys = 0
    wrong_types = 0
    invalid_values = 0
    out_of_range = 0
    invalid_keys = 0
    empty_levels = 0
    warning_count = 0
    train_mode = False
    allowed_supplies = []

    def __init__(self, filename, train_mode=False):
        '''
        Load in the file and parse the yaml
        '''
        self.file = self.validate_file_location(filename)
        try:
            self.api_file = open(API_YAML)
            self.api_yaml = yaml.load(self.api_file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.FATAL, "Error while loading in api yaml. Please check the .env to make sure the location is correct and try again.\n\n" + str(e) + "\n")
        try:
            self.state_change_file = open(STATE_YAML)
            self.state_changes_yaml = yaml.load(self.state_change_file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.FATAL, "Error while loading in state api yaml. Please check the .env to make sure the location is correct and try again.\n\n" + str(e) + "\n")
        try:
            self.loaded_yaml = yaml.load(self.file, Loader=yaml.CLoader)
            try:
                dup_check_file = open(filename, 'r')
                yaml.load(dup_check_file, Loader=UniqueKeyLoader)
            except Exception as e:
                self.logger.log(LogLevel.FATAL, "Error while loading in yaml file -- " + str(e))
        except Exception as e:
            self.logger.log(LogLevel.FATAL, "Error while loading in yaml file. Please ensure the file is a valid yaml format and try again.\n\n" + str(e) + "\n")
        try:
            self.dep_file = open(DEP_JSON)
            self.dep_json = json.load(self.dep_file)
        except Exception as e:
            self.logger.log(LogLevel.FATAL, "Error while loading in json dependency file. Please check the .env to make sure the location is correct and try again.\n\n" + str(e) + "\n")
        self.train_mode = train_mode
        api = copy.deepcopy(self.api_yaml)
        self.allowed_supplies = copy.deepcopy(api['components']['schemas']['SupplyTypeEnum']['enum'])
        if not self.train_mode:
            for x in self.dep_json['trainingOnlySupplies']:
                self.allowed_supplies.remove(x)

        for character in self.loaded_yaml.get('state', {'characters': []})['characters']:
            if character.get('has_blanket', False):
                self.invalid_keys += 1 
                self.logger.log(LogLevel.WARN, f"Blankets can't appear on characters at startup but '{character.get('id')}' has 'has_blanket' set to True.")

        self.branches = self.find_all_branch_segments(copy.deepcopy(self.loaded_yaml))


    def __del__(self):
        '''
        Basic cleanup: closing the file loaded in on close.
        '''
        self.logger.log(LogLevel.DEBUG, "Program closing...")
        if (self.file):
            self.file.close()
        if (self.api_file):
            self.api_file.close()
        if (self.state_change_file):
            self.state_change_file.close()
        if (self.dep_file):
            self.dep_file.close()
        if (self.dup_check_file):
            self.dup_check_file.close()


    def find_all_branch_segments(self, data):
        '''
        Creates and returns a list of all scene branches.
        '''
        paths = self.get_branches_from_scene(data, self.determine_first_scene(data)['id'])

        # remove duplicates (same order, same elements)
            
        def find_el_in_list(lst, el):
            inds_where_found = []
            for ind in range(len(lst)):
                x = lst[ind]
                if len(x) == len(el):
                    found_match = True
                    for i in range(len(x)):
                        if x[i] != el[i]:
                            found_match = False
                            break
                    if found_match:
                        inds_where_found.append(ind)
            return inds_where_found
        
        new_paths = []
        for p in paths:
            if len(p) > 0:
                inds = find_el_in_list(paths, p)
                try:
                    new_paths.index(paths[inds[0]])
                except:
                    new_paths.append(paths[inds[0]])

        return new_paths


    def get_branches_from_scene(self, data, scene_id, path=[]):
        '''
        Given a starting scene_id, updates the path with branches
        that can be taken from that scene
        '''
        paths = []
        scenes = data['scenes']
        scene = self.get_scene_by_id(scenes, scene_id)
        scene_ind = scenes.index(scene)
        default_next = scene.get('next_scene', scenes[scene_ind+1]['id'] if scene_ind+1 < len(scenes) else None) 
        for a in scene['action_mapping']:
            action_path = copy.deepcopy(path)
            next_scene = a.get('next_scene', default_next)
            if next_scene is None:
                paths.append(path)
                return paths
            if action_path.count(next_scene) < 2:
                if len(action_path) == 0:
                    action_path = [scene_id, next_scene]
                else:
                    action_path.append(next_scene)
                paths += self.get_branches_from_scene(data, next_scene, action_path)
            else:
                paths.append(path)
                return paths
        return paths
    

    def validate_field_names(self):
        '''
        Ensures all fields are supported by the API
        '''
        # start by checking the top level
        schema = self.api_yaml['components']['schemas']
        top_level = schema['Scenario']['properties']
        required = schema['Scenario']['required'] if 'required' in schema['Scenario'] else []
        return self.validate_one_level('top', self.loaded_yaml, top_level, required, self.api_yaml)


    def validate_one_level(self, level_name, to_validate, type_obj, required, api_yaml, persist_characters=False):
        '''
        Takes in an object to validate (to_validate) and the yaml schema describing the 
        expected types (type_obj)
        '''
        is_valid = True
        found_keys = []
        
        # do not require characters if persist_characters is true
        if level_name == 'scenes':
            persist_characters = to_validate.get('persist_characters')
        if level_name == 'Scenes/State' and persist_characters:
            if 'characters' in required:
                required.remove('characters')

        if level_name == 'supplies':
            if to_validate.get('type') not in self.allowed_supplies and to_validate.get('quantity') > 0:
                self.logger.log(LogLevel.ERROR, f"Since eval mode is true, supplies must only be one of {self.allowed_supplies}, but '{to_validate.get('type')}' was found.")
                self.invalid_values += 1

        # see if an object is empty (and if it's allowed to be)
        if to_validate == None and len(required) == 0:
            return True
        elif to_validate == None and len(required) > 0:
            self.logger.log(LogLevel.ERROR, "Level '" + level_name + "' is empty but must contain keys " + str(required))
            self.empty_levels += 1
            return False
        
        # loop through keys to check each value against expectations
        for key in to_validate:
            # make sure it is a valid key
            if key not in type_obj:
                self.logger.log(LogLevel.ERROR, "'" + key + "' is not a valid key at the '" + level_name + "' level of the yaml file. Allowed keys are " + str(list(type_obj.keys())))
                self.invalid_keys += 1
                is_valid = False
            else:
                # begin type-checking
                this_key_data = type_obj[key]
                # check for the 'type' property - otherwise it might only have a $ref
                if 'type' in this_key_data:
                    key_type = type_obj[key]['type']
                    # Basic types listed in PRIMITIVE_TYPE_MAP
                    if key_type in PRIMITIVE_TYPE_MAP:
                        if not self.validate_primitive(to_validate[key], key_type, key, level_name, type_obj[key]):
                            is_valid = False
                    # check for objects (key:value pairs)
                    elif key_type == 'object':
                        if 'additionalProperties' in type_obj[key]:
                            if not self.validate_additional_properties(type_obj[key], to_validate[key], key, level_name, api_yaml):
                                is_valid = False
                        else:
                            self.logger.log(LogLevel.FATAL, "API error: Missing additionalProperties on '" + key + "' object at the '" + level_name + "' level. Please contact TA3 for assistance.")
                            return False
                        
                    elif key_type == 'array':
                        if not self.validate_array(to_validate[key], key, level_name, key_type, type_obj, api_yaml):
                            is_valid = False
                    else:
                        self.logger.log(LogLevel.FATAL, "API error: Unhandled validation for type '" +  key_type + "' at the " + level_name + "' level. Please contact TA3 for assistance.")
                        return False
                        
                # check deep objects (more than simple key-value)
                elif '$ref' in this_key_data:
                    # get the ref type and check that location (skip starting hashtag)
                    location = type_obj[key]['$ref'].split('/')[1:]
                    if level_name == 'scenes' and location[len(location)-1] == 'State':
                        # state at the scenes level should follow state_changes.yaml
                        if not self.validate_state_change(to_validate[key], persist_characters):
                            is_valid = False
                    else:
                        ref_loc = api_yaml
                        # access the currect location to get the type map
                        for x in location:
                            ref_loc = ref_loc[x]
                        if 'enum' in ref_loc:
                            if not self.validate_enum(ref_loc, key, level_name, to_validate[key]):
                                is_valid = False
                        elif isinstance(to_validate[key], dict):
                            if not self.validate_object(to_validate[key], ref_loc, key, level_name, type_obj[key]['$ref'], api_yaml):
                                is_valid = False
                        else:
                            self.log_wrong_type(key, level_name, location[len(location)-1], type(to_validate[key]))
                            is_valid = False 
                else:
                    self.logger.log(LogLevel.FATAL, "API Error: Key '" + key + "' at level '" + level_name + "' has no defined type or reference. Please contact TA3 for assistance.")
                    return False
            found_keys.append(key)
        # check for missing keys
        for key in type_obj:
            if key not in found_keys:
                if (key in required):
                    self.logger.log(LogLevel.ERROR, "Required key '" + key + "' at level '" + level_name + "' is missing in the yaml file.")
                    self.missing_keys += 1
                    is_valid = False
                else:
                    self.logger.log(LogLevel.DEBUG, "Optional key '" + key + "' at level '" + level_name + "' is missing in the yaml file.")
        
        if level_name == 'characters':
            if 'injuries' in to_validate:
                injury_count = sum(1 for injury in to_validate['injuries'] if injury['name'] not in ['Ear Bleed', 'Asthmatic', 'Internal'] and 'Broken' not in injury['name'])
                if injury_count > 8 and not self.train_mode:
                    self.logger.log(LogLevel.ERROR, f"Character '{to_validate.get('name')}' has {injury_count} 'masked' injuries (punctures, lacerations, burns), which exceeds the maximum of 8 allowed in the simulation.")

        return is_valid
    

    def determine_first_scene(self, data):
        '''
        Determine the first scene, either from 'first_scene' or the first in the scenes list.
        '''
        scenes = data.get('scenes', [])
        first_scene_id = data['first_scene'] if 'first_scene' in data else None
        
        if first_scene_id is None:
            return scenes[0]
        else:
            return self.get_scene_by_id(scenes, first_scene_id)
        

    def get_scene_by_id(self, scenes, scene_id):
        for x in scenes:
            if x['id'] == scene_id:
                return x


    def validate_state_change(self, obj_to_validate, persist_characters=False):
        '''
        Under Scenes in the API, state should be defined slightly differently.
        Use state_changes.yaml and perform as before.
        '''
        schema = self.state_changes_yaml['components']['schemas']
        top_level = schema['State']['properties']
        required = schema['State']['required'] if 'required' in schema['State'] else []
        return self.validate_one_level('Scenes/State', obj_to_validate, top_level, required, self.state_changes_yaml, persist_characters)


    def validate_enum(self, type_obj, key, level, item):
        '''
        Accepts as parameters the object that describes expected types, 
        the key of the object, the level we're looking at, and the value 
        to check        
        '''
        is_valid = True
        # we are expecting a string here (will this ever be an int/float?)
        if isinstance(item, str):
                allowed = type_obj['enum']
                if item not in allowed:
                    self.logger.log(LogLevel.ERROR, "Key '" + key + "' at level '" + level + "' must be one of the following values: " + str(allowed) + " but is '" + item + "' instead.")
                    self.invalid_values += 1
                    is_valid = False
        else:
            self.log_wrong_type(key, level, str(str), type(item))
            is_valid = False 
        return is_valid


    def validate_object(self, item, location, key, level, ref_name, api_yaml):
        '''
        Checks if an item matches the reference location. The reference location
        may reference a full object, small object, or enum. Checks all 3 possibilities.
        '''
        is_valid = True
        # check large object
        if 'properties' in location:
            if not self.validate_one_level(key, item, location['properties'], location['required'] if 'required' in location else [], api_yaml):
                is_valid = False
        # check small object
        elif 'additionalProperties' in location:
            if not self.validate_additional_properties(location, item, key, level, api_yaml):
                is_valid = False
        # check enum
        elif 'enum' in location:
            if not self.validate_enum(location, key, level, item):
                is_valid = False
        else:
            self.logger.log(LogLevel.FATAL, "API missing enum, property, or additional properties for '" + ref_name + "'. Cannot parse. Please contact TA3 for assistance.")
        return is_valid
    

    def validate_additional_properties(self, type_obj, item, key, level, api_yaml):
        '''
        Accepts an object that describes the type we're looking for and an item to validate
        '''
        is_valid = True
        if 'type' in type_obj['additionalProperties']:
            val_type = type_obj['additionalProperties']['type']
            # two types of objects exist: 1. list of key-value 
            if isinstance(item, list):
                for pair_set in item:
                    for k in pair_set:
                        if not self.do_types_match(pair_set[k], PRIMITIVE_TYPE_MAP[val_type]):
                            self.log_wrong_type(k, level, val_type, type(pair_set[k]))
                            is_valid = False
            # 2. object with key-value
            else:
                if isinstance(item, dict):
                    for k in item:
                        if not self.do_types_match(item[k], PRIMITIVE_TYPE_MAP[val_type]):
                            self.log_wrong_type(k, level, val_type, type(item[k]))
                            is_valid = False
                else:
                    self.log_wrong_type(key, level, 'object', type(item))
                    is_valid = False 
        elif '$ref' in type_obj['additionalProperties']:
            location = type_obj['additionalProperties']['$ref'].split('/')[1:]
            ref_loc = api_yaml
            for x in location:
                ref_loc = ref_loc[x]
            if isinstance(item, list):
                for pair_set in item:
                    for k in pair_set:
                        if not self.validate_object(pair_set[k], ref_loc, key, level, type_obj['additionalProperties']['$ref'], api_yaml):
                            is_valid = False
            else:
                if isinstance(item, dict):
                    for k in item:
                        if not self.validate_object(item[k], ref_loc, key, level, type_obj['additionalProperties']['$ref'], api_yaml):
                            is_valid = False
                else:
                    self.log_wrong_type(key, level, 'object', type(item))
                    is_valid = False      
        else:
            self.logger.log(LogLevel.FATAL, "API Error: Additional Properties must either have a type or ref, but at level '" + level + "' for property '" + key + "' it does not. Please contact TA3 for assistance.")
            return False
        return is_valid


    def validate_array(self, item, key, level, key_type, typed_keys, api_yaml):
        '''
        Looks at an array and ensures that each item in the array matches expectations
        '''
        is_valid = True
        if not isinstance(item, list):
            self.log_wrong_type(key, level, key_type, type(item))
            is_valid = False
        else:
            # get type of item in array and check that each item matches
            item_type = typed_keys[key]['items']
            # check complex object types 
            if '$ref' in item_type:
                location = item_type['$ref'].split('/')[1:]
                ref_loc = api_yaml
                for x in location:
                    ref_loc = ref_loc[x]
                for i in item:
                    if not self.validate_object(i, ref_loc, key, level, typed_keys[key]['items']['$ref'], api_yaml):
                        is_valid = False
            # check basic types
            elif 'type' in item_type:
                expected = item_type['type']
                if expected in PRIMITIVE_TYPE_MAP:
                    for i in item:
                        if not self.validate_primitive(i, expected, key, level, item_type):
                            is_valid = False
            else:
                self.logger.log(LogLevel.FATAL, "API Error: Missing type definition or reference at level '" + level + "' for property '" + key + "'. Please contact TA3 for assistance.")
                return False
        return is_valid
    

    def validate_primitive(self, item, expected_type, key, level, type_obj):
        '''
        Looks at an object against an expected primitive type to see if it matches
        '''
        is_valid = True 
        # first validate enums
        if PRIMITIVE_TYPE_MAP[expected_type] == str and 'enum' in type_obj:
            if not self.validate_enum(type_obj, key, level, item):
                is_valid = False
        # then validate the rest
        elif not self.do_types_match(item, PRIMITIVE_TYPE_MAP[expected_type]):
            self.log_wrong_type(key, level, expected_type, type(item))
            is_valid = False
        if is_valid:
            # check for min/max only if type is valid
            if 'minimum' in type_obj:
                if item < type_obj['minimum']:
                    is_valid = False
                    self.logger.log(LogLevel.ERROR, "Key '" + key + "' at level '" + level + "' has a minimum of " + str(type_obj['minimum']) + " but is " + str(item) + ". (" + str(item) + " < " + str(type_obj['minimum']) + ")")
                    self.out_of_range += 1
            if 'maximum' in type_obj:
                if item > type_obj['maximum']:
                    is_valid = False
                    self.logger.log(LogLevel.ERROR, "Key '" + key + "' at level '" + level + "' has a maximum of " + str(type_obj['maximum']) + " but is " + str(item) + ". (" + str(item) + " > " + str(type_obj['maximum']) + ")")
                    self.out_of_range += 1
        return is_valid


    def do_types_match(self, item, type):
        '''
        Checks the basic data types, allowing integers in place of floats and ints and floats in place of strings (think stringified numbers)
        '''
        return isinstance(item, type) or (type == float and isinstance(item, int)) or (type == str and (isinstance(item, float) or isinstance(item, int)))


    def log_wrong_type(self, key, level, expected, actual):
        '''
        Logs when an incorrect type is found for a key
        '''
        self.logger.log(LogLevel.ERROR, "Key '" + key + "' at level '" + level + "' should be type '" + expected + "' but is " + str(actual) + " instead.")
        self.wrong_types += 1
    

    def validate_file_location(self, filename):
        '''
        Try to load in the yaml file. Checks that a path has been given, that the path leads to a yaml file,
        and that the file is found. Returns the open binary file object.
        '''
        if not filename:
            self.logger.log(LogLevel.FATAL, "No filename received. To run, please use 'python3 validator.py -f [filename]'")
        if not filename.strip().endswith('.yaml'):
            self.logger.log(LogLevel.FATAL, "File must be a yaml file.")
        try:
            f = open(filename, 'r')
            return f
        except:
            self.logger.log(LogLevel.FATAL, "Could not open file " + filename + ". Please make sure the path is valid and the file exists.")


    def validate_dependencies(self):
        '''
        Checks the yaml file against the dependency requirements to check for 
        additional required/ignored fields and specific value requirements
        '''
        self.simple_requirements()
        self.conditional_requirements()
        self.conditional_forbid()
        self.simple_value_matching()
        self.deep_links()
        self.value_follows_list()
        self.require_unstructured()
        self.scenes_with_state()
        self.validate_action_params()
        self.validate_mission_importance()
        self.character_matching()
        self.verify_uniqueness()
        self.verify_allowed_actions()
        self.check_first_scene()
        self.is_pulse_oximeter_configured()
        self.check_scene_env_type()


    def simple_requirements(self):
        '''
        Checks the yaml file for simple required dependencies.
        If field 1 is provided, then field2 is required
        '''
        for req in self.dep_json['simpleRequired']:
            loc = req.split('.')
            all_found = self.property_meets_conditions(loc, copy.deepcopy(self.loaded_yaml))
            for x in all_found:
                found = x.split('.')
                if found[len(found)-1] != loc[len(loc)-1]:
                    # possible that we thought we found a key but didn't. if so, skip
                    continue 
                else:
                    # start searching for the key(s) that is/are required now that the first key has been found
                    self.search_for_key(True, found, self.dep_json['simpleRequired'][req], "has been provided")


    def property_meets_conditions(self, first_key_list, data, value='', length=-1, exists=True, loc=[]):
        '''
        Accepts a list of deepening keys to search through, where
        the last key is the key to find if it exists in data.
        Then checks if certain conditions are met.
        Returns the paths of the found keys that meet conditions.
        '''
        if len(loc) == 0:
            loc = first_key_list
        found_indices = []
        skip = False
        for i in range(len(first_key_list)):
            k = first_key_list[i]
            # check through each element of the array for keys
            if '[]' in k:
                simple_k = k.split('[]')[0]
                if data is not None and simple_k in data:
                    data = data[simple_k]
                    data = data if data is not None else []
                    for j in range(len(data)):
                        # add in indices where keys were found
                        if (isinstance(data, object) and j in data) or isinstance(data, list):
                            detailed_k = simple_k + '[' + str(j) + ']'
                            found_indices += (self.property_meets_conditions(first_key_list[i+1:], data[j], value=value, length=length, exists=exists, loc='.'.join(loc).replace(k, detailed_k).split('.')))
                else:
                    # key is not here, don't keep searching
                    skip = True
                    break
            else:
                if data is not None and k in data:
                    data = data[k]
                else:
                    # key is not here, don't keep searching
                    skip = True
                    break
        if not skip and exists:
            valid = True
            # check for specific value
            if value != '':
                if str(data) != str(value):
                    valid = False 
            # check for array length
            if length > -1:
                if len(data) < length:
                    valid = False
            if valid:
                found_indices.append('.'.join(loc))
        elif skip and not exists:
            # key did not exist and we didn't want it to
            loc = '.'.join(loc)
            if '[]'  not in loc:
                found_indices.append(loc)
        return found_indices


    def search_for_key(self, should_find, found, expected_required, explanation, expected_val=[]):
        '''
        Searches for a key that is either required or ignored based on the additional dependencies. 
        @param should_find is a boolean of if we need this key or don't need this key
        @param found is the list of locations where the original key was found that
        forced this key to be required or not. 
        @param expected_required is the list of locations where we expect to find 
        keys
        @param explanation is a string explanation of why the key is expected (or not), in case of an error
        @param expected_val is a list of possible/allowed expected values for each key found, if applicable
        '''
        for required in expected_required:
            # go through the path to the location we found and the requirement
            # side-by-side as long as possible
            required = required.split('.')
            data = copy.deepcopy(self.loaded_yaml)
            earlyExit = False
            for i in range(min(len(found), len(required))):
                if found[i].split('[')[0] == required[i].split('[')[0]:
                    # they are the same!
                    if '[]' in required[i]:
                        # handle arrays
                        ind = int(found[i].split('[')[1].replace(']', ''))
                        data = data[required[i].split('[]')[0]][ind] 
                    else:
                        # handle non-arrays
                        data = data[required[i]]
                else:
                    # difference found, break
                    required = required[i:]
                    earlyExit = True
                    break
            if not earlyExit:
                required = required[i+1:]
            # look through data for required
            found_key = True
            for k in required:
                if '[]' in k:
                    self.logger.log(LogLevel.FATAL, "No index provided for required key '" + k + "'. Cannot proceed.")
                    return
                if k in data:
                    data = data[k]
                else:
                    if should_find:
                        # we expected to find this key, error
                        self.logger.log(LogLevel.ERROR, "Key '" + k + "' is required because '" + '.'.join(found) + "' " + explanation + ", but it is missing.")
                        self.missing_keys += 1
                    else:
                        # otherwise, we did not want to find the key, so we're good here
                        found_key = False
                        break
            if should_find is not None and not should_find and found_key:
                self.logger.log(LogLevel.ERROR, "Key '" + k + "' is not allowed because '" + '.'.join(found) + "' " + explanation + ".")
                self.invalid_keys += 1
            elif found_key and len(expected_val) > 0:
                if data not in expected_val:
                    self.logger.log(LogLevel.ERROR, "Key '" + k + "' must have one of the following values " + str(expected_val) + " because '" + '.'.join(found) + "' " + explanation + ", but instead value is '" + str(data) + "'")
                    self.invalid_values += 1
                    

    def conditional_requirements(self):
        '''
        Checks the yaml file for simple required dependencies.
        If field 1 is provided and meets a set of conditions, then field 2 is required
        '''
        for req in self.dep_json['conditionalRequired']:
            loc = req.split('.')
            # there may be more than one if-else for each key, look through each
            for entry in self.dep_json['conditionalRequired'][req]:
                value = entry['conditions']['value'] if 'value' in entry['conditions'] else ''
                length = entry['conditions']['length'] if 'length' in entry['conditions'] else -1
                all_found = self.property_meets_conditions(loc, copy.deepcopy(self.loaded_yaml), value=value, length=length)
                for x in all_found:
                    found = x.split('.')
                    if found[len(found)-1] != loc[len(loc)-1]:
                        # possible that we thought we found a key but didn't. if so, skip
                        continue 
                    else:
                        # start searching for the key(s) that is/are required now that the first key has been found
                        self.search_for_key(True, found, entry['required'], "meets conditions " + str(entry['conditions']))


    def conditional_forbid(self):
        '''
        Checks the yaml file for simple required dependencies.
        If field 1 is provided and meets a set of conditions, then field 2 should not be provided
        '''
        for req in self.dep_json['conditionalForbid']:
            loc = req.split('.')
            # there may be more than one if-else for each key, look through each
            for entry in self.dep_json['conditionalForbid'][req]:
                value = entry['conditions']['value'] if 'value' in entry['conditions'] else ''
                length = entry['conditions']['length'] if 'length' in entry['conditions'] else -1
                exists = bool(entry['conditions']['exists']) if 'exists' in entry['conditions'] else True
                all_found = self.property_meets_conditions(loc, copy.deepcopy(self.loaded_yaml), value=value, length=length, exists=exists)
                for x in all_found:
                    found = x.split('.')
                    if found[len(found)-1] != loc[len(loc)-1]:
                        # possible that we thought we found a key but didn't. if so, skip
                        continue 
                    else:
                        # start searching for the key(s) that is/are required now that the first key has been found
                        self.search_for_key(False, found, entry['forbid'], "meets conditions " + str(entry['conditions']))


    def simple_value_matching(self):
        '''
        Checks the yaml file for value-matching dependencies.
        If field1 equals value1, then field2 must be one of [...values]
        '''
        for field in self.dep_json['simpleAllowedValues']:
            loc = field.split('.')
            # there may be more than one value for each key, look through each
            for val in self.dep_json['simpleAllowedValues'][field]:
                # find every place where the field matches the value
                all_found = self.property_meets_conditions(loc, copy.deepcopy(self.loaded_yaml), value=val)
                for x in all_found:
                    found = x.split('.')
                    if found[len(found)-1] != loc[len(loc)-1]:
                        # possible that we thought we found a key but didn't. if so, skip
                        continue 
                    else:
                        # start searching for the key(s) that need to match one of the provided values
                        for key in self.dep_json['simpleAllowedValues'][field][val]:
                            self.search_for_key(None, found, [key], "is '" + val + "'", self.dep_json['simpleAllowedValues'][field][val][key])


    def require_unstructured(self):
        '''
        Within every scenes[].state, at least one unstructured field must be provided.
        '''
        data = copy.deepcopy(self.loaded_yaml)
        i = 0
        for scene in data['scenes']:
            if 'state' in scene:
                state = scene['state']
                # look for an unstructured field
                found = self.find_unstructured(state)
                if not found:
                    # unstructured not found - error
                    self.logger.log(LogLevel.ERROR, "At least one 'unstructured' key must be provided within each scenes[].state but is missing at scene[" + scene['id'] + "]")
                    self.missing_keys += 1
            i += 1


    def find_unstructured(self, obj):
        '''
        Looks through obj for an unstructured field
        '''
        found = False
        if obj is None:
            return found
        for k in obj:
            if isinstance(obj[k], dict):
                found = found or self.find_unstructured(obj[k])
            if k == 'unstructured':
                found = True
        return found


    def deep_links(self):
        '''
        Checks the yaml file for "if field1 is one of [a, b,...] and field2 is one of [c, d,...],
        then field3 must be one of [e, f,...]"
        '''
        for parent_key in self.dep_json['deepLinks']:
            # get all possible parents for the keys
            possible_parents = self.property_meets_conditions(parent_key.split('.'), copy.deepcopy(self.loaded_yaml))
            for p in possible_parents:
                if '[]' in p:
                    # no index given for an array, skip this key
                    continue
                # look for matching keys using possibleParents
                for req_set in self.dep_json['deepLinks'][parent_key]:
                    conditions = True
                    # check if the conditions are true
                    explanation = "key-value pairs "
                    for c in req_set['condition']:
                        singleCondition = False
                        values = req_set['condition'][c]
                        if not isinstance(values, list):
                            values = [values]
                        for v in values:
                            singleCondition = singleCondition or self.does_key_have_value(p.split('.')+c.split('.'), v, copy.deepcopy(self.loaded_yaml))
                            if singleCondition:
                                explanation += "('" + c + "': '" + str(v) + "'); "
                                break
                        conditions = conditions and singleCondition
                    # remove extra semicolon
                    explanation = explanation[:-2]
                    if conditions:
                        # if the conditions match at this parent level, check if the required keys also match
                        for x in req_set['requirement']:  
                            self.search_for_key(None, p.split('.'), [parent_key+'.'+x], 'has ' + explanation, expected_val=req_set['requirement'][x])
            

    def does_key_have_value(self, key, value, yaml):
        '''
        Looks through the yaml file to see if a key at a specific location has the given value
        '''
        val = self.get_value_at_key(key, yaml)
        if val is not None:
            # if we made it to here, we found the key - check the value!
            return val == value
        return False


    def get_value_at_key(self, key, yaml):
        '''
        Given a key, returns the value matching
        '''
        data = yaml
        for k in key:
            if '[' in k:
                loc = k.split('[')[0]
                inside_brackets = k.split('[')[1].split(']')[0]
                if inside_brackets is not None and inside_brackets != '':
                    ind = int(k.split('[')[1].split(']')[0])
                    if loc in data:
                        data = data[loc]
                        if len(data) > ind:
                            data = data[ind]
                else:
                    return None
            elif k in data:
                data = data[k]
            else:
                # key not found
                return None
        return data


    def value_follows_list(self):
        '''
        Checks the yaml file for "field1 value must match one of the values from field2"
        '''
        for key in self.dep_json['valueMatch']:
            # start by compiling a list of all allowed values by using the value of the k-v pair
            allowed_loc = self.dep_json['valueMatch'][key].split('.')
            locations = self.property_meets_conditions(allowed_loc, copy.deepcopy(self.loaded_yaml))
            # gather allowed values
            allowed_values = []
            for l in locations:
                loc = l.split('.')
                val = self.get_value_at_key(loc, copy.deepcopy(self.loaded_yaml))
                if val is not None:
                    allowed_values.append(val)
            # check if the location matches one of the allowed values
            locations = self.property_meets_conditions(key.split('.'), copy.deepcopy(self.loaded_yaml))
            for loc in locations:
                v = self.get_value_at_key(loc.split('.'), copy.deepcopy(self.loaded_yaml))
                if v not in allowed_values:
                    self.logger.log(LogLevel.ERROR, "Key '" + loc.split('.')[-1] + "' at '" + str(loc) + "' must have one of the following values " + str(allowed_values) + " to match one of " + str('.'.join(allowed_loc)) + ", but instead value is '" + str(v) + "'")
                    self.invalid_values += 1


    def character_matching(self):
        '''
        Checks the yaml file for character matches: "characters at scene level 0 must match state characters. 
        characters at other scene levels must match the characters within that scene"
        '''
        # get all locations that have character ids 
        allowed_loc_0 = "state.characters[].id".split('.') # general location of character ids that are allowed in scene 0
        allowed_loc_other = "scenes[].state.characters[].id".split('.') # general location of characters listed in all other scenes
        removed_chars_loc = "scenes[].removed_characters[]".split('.') # general location of removed characters throughout the yaml
        data = copy.deepcopy(self.loaded_yaml)
        locations_0 = self.property_meets_conditions(allowed_loc_0, data) # specific locations of character ids that are allowed in scene 0
        locations_other = self.property_meets_conditions(allowed_loc_other, data) # specific locations of character ids that are listed in other scenes
        locations_removed = self.property_meets_conditions(removed_chars_loc, data) # specific locations of removed characters
        scenes = data['scenes'] 
        first_scene_id = self.determine_first_scene(data)['id']
        allowed_vals = {}
        allowed_vals[first_scene_id] = []
        all_chars = [] # store all characters found anywhere in the character definitions
        removed_chars = [] # store all removed characters that are found anywhere in the character definitions
        
        # get all allowed values, organizing by the scene index where those values will be allowed
        for l in locations_0:
            # getting allowed characters for the first scene
            loc = l.split('.')
            val = self.get_value_at_key(loc, data)
            if val is not None:
                allowed_vals[first_scene_id].append(val)   
                all_chars.append(val)

        for l in locations_other:
            # getting characters listed in all the other scenes
            ind = int(l.split('cenes[')[1].split(']')[0])
            if ind not in allowed_vals:
                allowed_vals[ind] = []
            loc = l.split('.')
            val = self.get_value_at_key(loc, data)
            if val is not None:
                allowed_vals[ind].append(val)   
                all_chars.append(val)

        for l in locations_removed:
            # get all characters removed at some point in the yaml
            val = self.get_value_at_key(l.split('.'), data)
            if val is not None:
                removed_chars.append(val)

        # prevent duplicate error messages for the same location
        missing_locs = []

        for loc in self.dep_json['characterMatching']:
            loc = loc.split('.')
            # find all locations where the property exists
            locations = self.property_meets_conditions(loc, data)
            for l in locations:
                # get the scene index
                ind = int(l.split('cenes[')[1].split(']')[0])
                s = scenes[ind]
                # check non-persistent-character scenes
                if (not s.get('persist_characters', False)) and ('characters' in s or s['id'] == first_scene_id):
                    # make sure the index exists in the allowed values dict
                    if ind not in allowed_vals and s['id'] != first_scene_id:
                        # path does not exist where we are checking for characters. Error (optionally, we don't want to send a duplicate!) and short circuit this run
                        where_vals_found = '.'.join(allowed_loc_0) if ind==0 else '.'.join(allowed_loc_other).replace('scenes[]', f'scenes[{ind}]')
                        if where_vals_found not in missing_locs and not self.get_value_at_key(where_vals_found.split('.')[:1], data):
                            missing_locs.append(where_vals_found)
                            self.logger.log(LogLevel.ERROR, "Path '" + str(where_vals_found) + "' does not exist.")
                            self.missing_keys += 1
                        continue
                    # all paths are available to continue; check that the value at the given location matches what we expect
                    loc = l.split('.')
                    val = self.get_value_at_key(loc, data)
                    # get the specific character ids allowed in this scene
                    this_allowed_vals = (allowed_vals[ind] if ind in allowed_vals else allowed_vals[first_scene_id])
                    if val is not None and val not in this_allowed_vals:
                        where_vals_found = '.'.join(allowed_loc_0) if s['id'] != first_scene_id else '.'.join(allowed_loc_other).replace('scenes[]', f'scenes[{ind}]')
                        self.logger.log(LogLevel.ERROR, "Key '" + loc[-1] + "' at '" + str('.'.join(loc)) + "' must have one of the following values " + str(this_allowed_vals) + " to match '" + str(where_vals_found) + "', but instead value is '" + str(val) + "'")
                        self.invalid_values += 1
                # check persist character scenes
                elif s.get('persist_characters', False):
                    scene_chars = self.get_characters_in_scene(data, s['id'])
                    loc = l.split('.')
                    removed_this_scene = s.get('removed_characters', [])
                    this_scene_characters = s.get('state', {}).get('characters', [])
                    this_scene_char_ids = []
                    for x in this_scene_characters:
                        this_scene_char_ids.append(x['id'])
                    val = self.get_value_at_key(loc, data)
                    if type(val) == type({}):
                        val = list(val.keys())[0]
                    if val is not None:
                        if val not in all_chars:
                            self.logger.log(LogLevel.ERROR, "Key '" + loc[-1] + "' at '" + str('.'.join(loc)) + "' has value '" + str(val) + "', but that character id is never defined within the scenario yaml file.")
                            self.invalid_values += 1
                        elif not any('removed_characters' in el for el in loc) and val in removed_this_scene:
                            self.logger.log(LogLevel.ERROR, f"Character ID '{val}' appears in '{str('.').join(loc)}', but is removed during this scene, so cannot be used.")
                            self.invalid_values += 1
                        elif val in scene_chars['removed'] and val not in this_scene_char_ids:
                            still_possible = False
                            for group in scene_chars['possible']:
                                if val in group:
                                    still_possible = True
                                    break
                            if still_possible:
                                self.logger.log(LogLevel.WARN, f"Character ID '{val}' appears in '{str('.').join(loc)}', but in some branches is removed prior to this scene. Ensure this character exists in every branch leading up to this scene.")
                                self.warning_count += 1    
                            else:
                                self.logger.log(LogLevel.ERROR, f"Character ID '{val}' appears in '{str('.').join(loc)}' but is never available to this scene due to prior removal.")
                                self.invalid_values += 1
                        else:
                            is_possible = False
                            for group in scene_chars['possible']:
                                if val in group:
                                    is_possible = True
                                    break
                            if not is_possible:
                                self.logger.log(LogLevel.ERROR, f"Character ID '{val}' appears in '{str('.').join(loc)}' but is never available to this scene.")
                                self.invalid_values += 1


    def verify_uniqueness(self):
        '''
        Ensure that all values at a certain level are unique
        '''
        for k in self.dep_json['unique']:
            loc = k.split('.')
            scope = self.dep_json['unique'][k]
            # find all locations where the property exists
            locations = self.property_meets_conditions(loc, copy.deepcopy(self.loaded_yaml))
            scope_locs = self.property_meets_conditions(scope.split('.'), copy.deepcopy(self.loaded_yaml))
            if scope == "":
                scope_locs = [""]
            for scope in scope_locs:
                vals_found = []
                if scope[-2:] == '[]':
                    # not an actual path
                    continue
                else:
                    for loc in locations:
                        if scope in loc or scope == "":
                            val = self.get_value_at_key(loc.split('.'), copy.deepcopy(self.loaded_yaml))
                            if val in vals_found:
                                self.logger.log(LogLevel.ERROR, f"Values from key '{k}' must be unique within scope '{scope if scope != '' else '[whole file]'}', but value '{val}' was found more than once.")
                                self.invalid_values += 1    
                            else:
                                vals_found.append(val)


    def scenes_with_state(self):
        '''
        Looks through the yaml file to make sure that every scene except the first has 
        a state field
        '''
        data = copy.deepcopy(self.loaded_yaml)
        scenes = data['scenes']
        first_scene_id = self.determine_first_scene(data)['id']
        for s in scenes:
            if s['id'] == first_scene_id:
                continue
            if 'state' not in s:
                self.logger.log(LogLevel.ERROR, "Key 'state' must be provided within all but the first entry in 'scenes' but is missing at scenes[" + s['id'] + "]")
                self.missing_keys += 1


    def verify_allowed_actions(self):
        '''
        Ensures that any action found in action_mapping is not in
        restricted_actions
        '''
        data = copy.deepcopy(self.loaded_yaml)
        scenes = data['scenes']
        for i in range(0, len(scenes)):
            if 'restricted_actions' in scenes[i] and 'action_mapping' in scenes[i]:
                for x in scenes[i]['action_mapping']:
                    if x['action_type'] in scenes[i]['restricted_actions']:
                        self.logger.log(LogLevel.ERROR, f"{x['action_type']} is a restricted action at scene with id '{scenes[i]['id']}', but appears in the action_mapping within that scene.")
                        self.invalid_values += 1

    def is_pulse_oximeter_configured(self): 
        '''
        Checks if Pulse Oximeter is configured in the supplies.
        '''
        # inital variables for getting specific data 
        data = copy.deepcopy(self.loaded_yaml)
        scenes = data['scenes']

        for scene in scenes:
            for action in scene.get('action_mapping', []):
                if action['action_type'] == 'CHECK_BLOOD_OXYGEN' or action['action_type'] == 'CHECK_ALL_VITALS':
                    possible_supplies = self.get_supplies_in_scene(data, scene['id'])
                    not_found = False
                    found = False
                    for lst in possible_supplies:
                        if any(s['type'] == 'Pulse Oximeter' and s['quantity'] > 0 for s in lst):
                            found = True
                        else:
                            not_found = True
                    if not_found:
                        if found:
                            # found in at least one path, but not found in at least one path - warning
                            self.warning_count += 1
                            self.logger.log(LogLevel.WARN, f"There might be an invalid action in scene '{scene['id']}'. A pulse oximeter must be available in order to have 'action type' equal to 'CHECK_BLOOD_OXYGEN' OR 'CHECK_ALL_VITALS', but in at least one branching path, the pulse oximeter is missing. Please ensure that a pulse oximeter is always available for this scene.")
                        else:
                            # not found in any paths
                            self.invalid_values += 1
                            self.logger.log(LogLevel.ERROR, f"There is an invalid action in scene '{scene['id']}'. A pulse oximeter must be available in order to have 'action type' equal to 'CHECK_BLOOD_OXYGEN' OR 'CHECK_ALL_VITALS' but is never available through any branching path. Please ensure that a pulse oximeter is always available for this scene.")
                        break


    def validate_action_params(self):
        '''
        Ensure that action parameters have valid values
        '''
        data = copy.deepcopy(self.loaded_yaml)
        api = copy.deepcopy(self.api_yaml)
        allowed_supplies = self.allowed_supplies
        allowed_locations = api['components']['schemas']['InjuryLocationEnum']['enum']
        allowed_categories = api['components']['schemas']['CharacterTagEnum']['enum']

        scenes = data['scenes']
        i = 0
        for scene in scenes:
            if 'action_mapping' in scene:
                map = scene['action_mapping']
                j = 0
                for action in map:
                    if 'parameters' in action:
                        params = action['parameters']
                        if 'treatment' in params:
                            if params['treatment'] not in allowed_supplies:
                                self.logger.log(LogLevel.ERROR, "Key 'scenes[" + scene['id'] + "].action_mapping[" + str(j) + "].parameters.treatment' must be one of the following values: " + str(allowed_supplies) + " but is '" + params['treatment'] + "' instead.")
                                self.invalid_values += 1                        
                        if 'location' in params:
                            if params['location'] not in allowed_locations:
                                self.logger.log(LogLevel.ERROR, "Key 'scenes[" + scene['id'] + "].action_mapping[" + str(j) + "].parameters.location' must be one of the following values: " + str(allowed_locations) + " but is '" + params['location'] + "' instead.")
                                self.invalid_values += 1 
                        if 'category' in params:
                            if params['category'] not in allowed_categories:
                                self.logger.log(LogLevel.ERROR, "Key 'scenes[" + scene['id'] + "].action_mapping[" + str(j) + "].parameters.category' must be one of the following values: " + str(allowed_categories) + " but is '" + params['category'] + "' instead.")
                                self.invalid_values += 1 
                        # validate params only includes expected values
                        for key in params:
                            if key not in ['treatment', 'location', 'category', 'evac_id']:
                                self.logger.log(LogLevel.ERROR, "'scenes[" + scene['id'] + "].action_mapping[" + str(j) + "].parameters' may only include the following keys: " + str(['treatment', 'location', 'category', 'evac_id']) + " but has key '" + key + "'.")
                                self.invalid_keys += 1 
                    j += 1
            i += 1


    def validate_mission_importance(self):
        '''
        Verifies that all characters with their mission importance appear
        in the critical_ids list.
        '''
        data = copy.deepcopy(self.loaded_yaml)
        # get all id/mission-importance pairs that appear throughout the entire scenario
        characters = data['state']['characters']
        character_importance = data.get('state', {}).get('mission', {}).get('character_importance', [])
        pairs = {}
        for scene in data['scenes']:
            characters += scene.get('state', {}).get('characters', [])
            character_importance += scene.get('state', {}).get('mission', {}).get('character_importance', [])
        for c in characters:
            cid = c['id']
            if 'mission_importance' in c['demographics']:
                importance = c['demographics']['mission_importance']
                pairs[cid] = importance 
            else:
                pairs[cid] = 'normal'  

        allowed_importance = copy.deepcopy(self.api_yaml)['components']['schemas']['MissionImportanceEnum']['enum']

        # verify that all pairs appear in character_importance
        critical_dict = {}
        for c in character_importance:
            critical_dict[list(c.items())[0][0]] = list(c.items())[0][1]
        for k in critical_dict:
            if k in pairs:
                if pairs[k] != critical_dict[k]:
                    self.logger.log(LogLevel.ERROR, "Value of 'mission.character_importance['" + k + "']' is '" + str(critical_dict[k]) + "', but the character's mission_importance is '" + str(pairs[k]) + "'")
                    self.invalid_values += 1     
            else:
                # will be handled by character_matching. Do not double count error!
                pass  
            if critical_dict[k] not in allowed_importance:
                self.logger.log(LogLevel.ERROR, "Value of 'mission.character_importance['" + k + "']' must be one of " + str(allowed_importance) + "', but instead it is '" + critical_dict[k] + "'")
                self.invalid_values += 1              
        for k in pairs:
            if k not in critical_dict and pairs[k] != 'normal':
                self.logger.log(LogLevel.ERROR, "Value of 'mission.character_importance' is missing pair ('" + k + "', '" + str(pairs[k]) + "')")
                self.missing_keys += 1         


    def check_first_scene(self):
        '''
        Makes sure the first scene is compliant with all the rules we give it:
        1. must not contain state
        '''
        data = copy.deepcopy(self.loaded_yaml)

        # Use determine_first_scene to get the first scene
        first_scene = self.determine_first_scene(data)

        if 'state' in first_scene: 
            self.logger.log(LogLevel.ERROR, "Key 'state' is not allowed in the first scene")
            self.invalid_keys += 1


    def check_scene_env_type(self):
        '''
        Checks to make sure if a scene state defines sim_environment, the type is not 
        different from the type defined in scenario.sim_environment
        '''
        data = copy.deepcopy(self.loaded_yaml)
        orig_type = data['state']['environment']['sim_environment']['type']
        scenes = data['scenes']
        for scene in scenes:
            if 'state' in scene and 'environment' in scene['state'] and 'sim_environment' in scene['state']['environment']:
                new_type = scene['state']['environment']['sim_environment'].get('type', None)
                if new_type is not None and new_type != orig_type:
                    self.warning_count += 1
                    self.logger.log(LogLevel.WARN, f"Key 'type' should not be redefined in scene states, but changes from '{orig_type}' to '{new_type}' in scene '{scene['id']}'. This redefinition will be ignored.")


    def get_characters_in_scene(self, data, scene_id):
        '''
        Gets all characters that could possibly be allowed in a scene
        '''
        def get_basic_chars(scene):
            characters = []
            for c in scene.get('state', {}).get('characters', []):
                characters.append(c['id'])
            return characters
        
        def get_removed_chars(scene):
            characters = []
            for c in scene.get('removed_characters', []):
                characters.append(c)
            return characters

        first_scene_id = self.determine_first_scene(data)['id']
        this_scene = self.get_scene_by_id(data['scenes'], scene_id)
        chars = {'possible': [], 'removed': []}
        if this_scene.get('persist_characters', False):
            segments = []
            for branch in self.branches:
                if scene_id in branch:
                    segments.append(branch[:branch.index(scene_id)+1])
            for segment in segments:
                tmp_chars = []
                tmp_removed = []
                for sid in segment:
                    if sid == first_scene_id:
                        # get scenario characters from first scene
                        tmp_chars += get_basic_chars(data)
                    else:
                        scene = self.get_scene_by_id(data['scenes'], sid)
                        if scene.get('persist_characters', False):
                            # modify allowed characters up to this point
                            tmp_chars += get_basic_chars(scene)
                            tmp_chars = list(set(tmp_chars))
                            for c in get_removed_chars(scene):
                                if sid != segment[-1]:
                                    if c in tmp_chars:
                                        tmp_chars.remove(c)
                                    if c not in tmp_removed:
                                        tmp_removed.append(c)
                        else:
                            # if persist characters is false at any point in the path, start fresh!
                            tmp_chars = get_basic_chars(scene)
                if len(tmp_chars) > 0:
                    chars['possible'].append(tmp_chars)
                chars['removed'] += tmp_removed
        elif this_scene['id'] != first_scene_id:
            chars['possible'] = [get_basic_chars(scene)]
        elif this_scene['id'] == first_scene_id:
            chars['possible'] = [get_basic_chars(data)]
        return chars


    def get_supplies_in_scene(self, data, scene_id):
        '''
        Gets the supplies that could be allowed in a scene
        '''
        def get_supplies(scene):
            return scene.get('state', {}).get('supplies', [])
        
        def override_supplies(cur, new):
            '''
            Only supplies defined in the supplies array are overwritten.
            All supplies left undefined are left unchanged
            '''
            if len(cur) == 0:
                return new
            for x in new:
                matching = [s for s in cur if s['type'] == x['type']]
                if len(matching) > 0:
                    cur[cur.index(matching[0])] = x
                else:
                    cur.append(x)
            return cur

        first_scene_id = self.determine_first_scene(data)['id']
        this_scene = self.get_scene_by_id(data['scenes'], scene_id)
        possible_supplies = []
        if this_scene.get('supplies', None) is None:
            segments = []
            for branch in self.branches:
                if scene_id in branch:
                    segments.append(branch[:branch.index(scene_id)+1])
            for segment in segments:
                tmp_possible = []
                for sid in segment:
                    if sid == first_scene_id:
                        # get scenario characters from first scene
                        tmp_possible = override_supplies(tmp_possible, get_supplies(data))
                    else:
                        # new supplies always overwrites previous supplies
                        scene = self.get_scene_by_id(data['scenes'], sid)
                        tmp_supplies = override_supplies(tmp_possible, get_supplies(scene))
                        if len(tmp_supplies) > 0:
                            tmp_possible = override_supplies(tmp_possible, get_supplies(scene))
                if len(tmp_possible) > 0:
                    possible_supplies.append(tmp_possible)
        elif this_scene['id'] != first_scene_id:
            possible_supplies = [get_supplies(scene)]
        elif this_scene['id'] == first_scene_id:
            possible_supplies = [get_supplies(data)]
        return possible_supplies
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ITM - YAML Validator')

    parser.add_argument('-f', '--filepath', dest='path', type=str, help='The path to the yaml file. Required if -u is not specified.')
    parser.add_argument('-u', '--update', dest='update', action='store_true', help='Switch to update the api files or not. Required if -f is not specified.')
    parser.add_argument('-t', '--train', dest='train', action='store_true', help="Validate a training scenario yaml")
    args = parser.parse_args()
    if args.update:
        generator = ApiGenerator()
        generator.generate_new_api()
        generator.generate_state_change_api()
    if args.update and not args.path:
        exit(0)
    file = args.path
    validator = YamlValidator(file, args.train)
    # validate the field names in the yaml
    validator.validate_field_names()
    # validate additional depdencies between fields
    validator.validate_dependencies()
    # print the answer for validity
    print("")

    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.missing_keys == 0 else "\033[91m") + "Missing Required Keys: " + str(validator.missing_keys))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.wrong_types == 0 else "\033[91m") + "Incorrect Data Type: " + str(validator.wrong_types))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.invalid_keys == 0 else "\033[91m") + "Invalid Keys: " + str(validator.invalid_keys))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.invalid_values == 0 else "\033[91m") + "Invalid Values (mismatched enum or dependency): " + str(validator.invalid_values))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.out_of_range == 0 else "\033[91m") + "Invalid Values (out of range): " + str(validator.out_of_range))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.empty_levels == 0 else "\033[91m") + "Properties Missing Data (empty level): " + str(validator.empty_levels))
    total_errors = validator.missing_keys + validator.wrong_types + validator.invalid_keys + validator.invalid_values + validator.empty_levels + validator.out_of_range
    print()
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if total_errors == 0 else "\033[91m") + "Total Errors: " + str(total_errors))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.warning_count == 0 else "\033[35m") + "Warnings: " + str(validator.warning_count))
    if total_errors == 0:
        validator.logger.log(LogLevel.CRITICAL_INFO, "\033[92m" + file + " is valid!")
    else:
        validator.logger.log(LogLevel.CRITICAL_INFO, "\033[91m" + file + " is not valid.")
