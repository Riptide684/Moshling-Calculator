from itertools import *
import numpy as np
import pickle


PLANT_TYPES = ("Love", "Pepper", "Orchid", "Apple", "Magic", "Frozen", "Star", "Dragon", "Daisy")
PLANT_COLOURS = ("Red", "Orange", "Yellow", "Green", "Blue", "Black", "Pink", "Purple")
EMPTY = ("", "")

res_plants = () # should contain the empty plant
res_plant_types = ()
other_modifiers = {}

moshling_recipes = {}
moshling_list = []

# a plant looks like ("Red", "Daisy")
# allow for plants of the form ("Any", "Dragon")
# the empty plant is ("", "")
# a garden is a sorted tuple of 3 plants


def plants_to_garden(plants):
    # input of form [("Red","Daisy"),...] of length <= 3
    # just ensures that the array is sorted and has the right length
    return tuple(sorted(list(plants) + [EMPTY for _ in range(3-len(plants))]))


def plant_to_text(plant):
    return plant[0] + " " + plant[1]


def print_garden(garden):
    # prints the text for the garden tuple
    print(", ".join([plant_to_text(plant) for plant in garden if plant != EMPTY]))


def text_to_plant(plant_text):
    # plant_text is of the form "Red,Daisy"
    return tuple(plant_text.split(","))


def seed_parents(seed):
    return [plant for plant in res_plants if plant[1] == seed]


class Recipe:
    # Reciple.plants is stored as an unsorted tuple of 3 plants (essentially the same as a garden)
    def __init__(self, plants):
        # plants should be an array of text of the form ["Red,Daisy","Blue,Apple","Any,Dragon"]
        self.plants = tuple(map(text_to_plant, plants))
        self.plant_types = tuple(sorted(set(plant[1] for plant in self.plants)))
        self.seeds = tuple(plant[1] for plant in self.plants)


    def __str__(self):
        return ", ".join([plant[0] + " " + plant[1] for plant in self.plants])
    

    def match(self, garden):
        # returns whether the given garden matches the recipe
        # note that Other can appear as a colour in the garden
        for perm in permutations(self.plants):
            # check if perm = garden, up to Any
            for i in range(3):
                if not (garden[i] == perm[i] or (perm[i][0] == "Any" and garden[i][1] == perm[i][1])):
                    break
            else:
                return True
            
        return False
    

def expand_any(plant):
    # accepts a plant and returns an array of all matching restricted plants (mostly used for matching Any)
    if plant[0] == "Any":
        return [res_plant for res_plant in res_plants if res_plant[1] == plant[1]]
    else:
        return [plant]


def import_recipes(filename):
    # file format should be {moshling name}:{seed colour},{seed type}; x3
    with open(filename, "r") as f:
        content = f.read().split("\n")

    for line in content:
        moshling_name = line.split(":")[0]
        recipe = Recipe(line.split(":")[1].split(";"))
        moshling_recipes[moshling_name] = recipe
        moshling_list.append(moshling_name)


def moshling_match(garden):
    # returns all moshlings that match the garden
    # SHOULD ONLY RETURN ONE

    matches = []
    
    for moshling in moshling_list:
        recipe = moshling_recipes[moshling]
        if recipe.match(garden):
            matches.append(moshling)

    return matches
    

class Action:
    # an action is digging up plants and then planting seeds
    def __init__(self, dig_targets, seeds):
        # dig_targets should be a tuple of plants
        # seeds is a tuple of plant types in text
        self.dig_targets = dig_targets
        self.seeds = seeds

    def __str__(self):
        text = "Dig: " + ", ".join(plant_to_text(plant) for plant in self.dig_targets) 
        text = text + "\nPlant: " + ", ".join(self.seeds)
        return text


def enumerate_good_gardens(moshling):
    # returns all gardens which attract the given moshling
    recipe_plants = moshling_recipes[moshling].plants
    plant_ranges = [expand_any(plant) for plant in recipe_plants]
    good_gardens = product(*[plant_ranges[i] for i in range(3)])

    ggs = set()
    for gg in good_gardens:
        ggs.add(tuple(sorted(gg)))

    return ggs


def enumerate_gardens(moshling):
    # returns an array of every possible garden, which are NOT GOOD
    possible_gardens = []
    l = len(res_plants)
    good_gardens = enumerate_good_gardens(moshling)

    for x in range(l):
        for y in range(x, l):
            for z in range(y, l):
                garden = tuple(sorted(res_plants[_] for _ in [x,y,z]))
                if garden not in good_gardens:
                    possible_gardens.append(garden)

    return possible_gardens


def enumerate_actions(garden):
    possible_actions = []

    plants = [plant for plant in garden if plant != EMPTY]
    possible_dig_targets = [list(set(combinations(plants, r))) for r in range(4)]

    # plant some seeds for each set of digs
    for num_digs in range(4):
        num_empty = garden.count(EMPTY) + num_digs
        for num_seeds in range(1, num_empty + 1):
            possible_seeds = combinations_with_replacement(res_plant_types, num_seeds)
            possible_actions = possible_actions + [Action(x[0], x[1]) for x in product(possible_dig_targets[num_digs], possible_seeds)]

    return possible_actions


class Policy:
    # a policy is just a transition matrix once we have fixed the actions
    def __init__(self, moshling):
        self.gardens = enumerate_gardens(moshling)
        self.policy_actions = {}
        self.transitions = np.zeros((len(self.gardens), len(self.gardens)))
        self.garden_to_index = {
            garden: i
            for i, garden in enumerate(self.gardens)
        }
        self.expectations = None


    def default_populate(self, recipe):
        # creates the default action to try and get the given recipe (one shot attempt + digging everything)
        seeds = recipe.seeds
        for garden in self.gardens:
            self.policy_actions[garden] = Action(tuple(plant for plant in garden if plant != EMPTY), seeds)

    
    def get_probabilities(self, garden, action):
        probabilities = np.zeros(self.transitions.shape[0])

        num_seeds = len(action.seeds)
        num_empty = garden.count(EMPTY) + len(action.dig_targets) - num_seeds
        # removes any one copy of the specified plants
        base_plants = [plant for plant in garden if plant != EMPTY]
        
        for dig_target in action.dig_targets:
            base_plants.remove(dig_target)

        for coloured_seeds in product(*[seed_parents(seed) for seed in action.seeds]):
            # plants all of the seeds and gives them the colour which is being looped over
            new_plants = base_plants + list(coloured_seeds)
            new_plants += [EMPTY for _ in range(num_empty)]
            new_plants.sort()
            new_garden = tuple(new_plants)
            # ignore good gardens (this may be a source of bugs)
            if new_garden not in self.garden_to_index:
                continue

            j = self.garden_to_index[new_garden]
            modifier = np.prod([other_modifiers[cs[1]] for cs in coloured_seeds if cs[0] == "Other"])
            probabilities[j] += modifier / (8 ** len(action.seeds))

        return probabilities


    def form_matrix(self):
        # fills out the transition matrix according to the policy actions
        self.transitions = np.zeros((len(self.gardens), len(self.gardens)))

        for garden in self.gardens:
            i = self.garden_to_index[garden]
            action = self.policy_actions[garden]
            self.transitions[i] = self.get_probabilities(garden, action)


    def evaluate(self):
        # assume that expected hitting time from each state is finite
        # now solve (I-P)h = 1
        n = self.transitions.shape[0]
        h = np.linalg.solve(np.eye(n) - self.transitions, np.ones(n))
        self.expectations = {garden: h[self.garden_to_index[garden]] for garden in self.gardens}

        return h


def calculate_optimal_policy(moshling, verbose=False):
    # initial policy needs to be proper, for example just planting all of the required plants immediately and then digging everything
    policy = Policy(moshling)

    policy.default_populate(moshling_recipes[moshling])
    policy.form_matrix()

    # now begin the process of evaluating and improving until we reach convergence
    iterations = 0
    max_iterations = 10
    stable = False
    stopping_parameter = 10e-8
    values = policy.evaluate()

    while not stable and iterations < max_iterations:
        new_actions = {}

        for garden in policy.gardens:
            best_q_value = 10e8
            best_action = None
            for action in enumerate_actions(garden):
                probabilities = policy.get_probabilities(garden, action)
                q_value = sum([probabilities[i] * values[i] for i in range(len(probabilities))])
                if q_value < best_q_value:
                    best_q_value = q_value
                    best_action = action

            if best_action == None:
                raise Exception("NO ACTION FOUND")
    
            new_actions[garden] = best_action

        policy.policy_actions = new_actions
        policy.form_matrix()
        new_values = policy.evaluate()

        if verbose:
            print(np.linalg.norm(new_values - values))

        if np.linalg.norm(new_values - values) < stopping_parameter:
            stable = True
        
        values = new_values

        iterations += 1

    if iterations == max_iterations:
        raise Exception("MAX ITERATIONS EXCEEDED")
    
    if verbose:
        print("Iterations: " + str(iterations))
        print(policy.policy_actions[plants_to_garden([])])
        print("Expected Time: " + str(policy.expectations[plants_to_garden([])]))

    return policy


def set_globals(moshling):
    recipe = moshling_recipes[moshling]
    global res_plant_types, res_plants, other_modifiers
    res_plant_types = recipe.plant_types
    colour_plants = tuple(sorted(set([plant for plant in recipe.plants if plant[0] != "Any"])))
    other_plants = tuple(("Other", plant_type) for plant_type in res_plant_types)
    res_plants = (EMPTY,) + other_plants + colour_plants

    # count how many colours the Other colours contain
    for pt in res_plant_types:
        other_hits = set()
        for plant in recipe.plants:
            if plant[0] != "Any" and plant[1] == pt:
                other_hits.add(plant)

        other_modifiers[pt] = 8 - len(other_hits)


def load_policy(moshling):
    with open('policies.pkl', 'rb') as f:
        loaded_actions = pickle.load(f)[moshling]

    policy = Policy(moshling)
    policy.policy_actions = loaded_actions
    policy.form_matrix()
    policy.evaluate()
    return policy


def load_all_policies():
    policies = {}

    with open('policies.pkl', 'rb') as f:
        loaded_actions = pickle.load(f)

    for moshling in moshling_list:
        set_globals(moshling)
        policy = Policy(moshling)
        policy.policy_actions = loaded_actions[moshling]
        policy.form_matrix()
        policy.evaluate()
        policies[moshling] = policy

    return policies


def query_moshling(moshling, plants=[], load=False, policy=None):
    set_globals(moshling)
    recipe = moshling_recipes[moshling]

    # firstly have to dig irrelevant plants
    garden = plants_to_garden(plants)
    extra_digs = tuple(plant for plant in garden if plant not in res_plants)
    garden = tuple(sorted(plant if plant in res_plants else EMPTY for plant in garden))

    if not policy:
        if load:
            policy = load_policy(moshling)
        else:
            policy = calculate_optimal_policy(moshling)

    if recipe.match(garden):
        expectation = 0
        action = Action([], [])
    else:
        expectation = policy.expectations[garden]
        action = policy.policy_actions[garden]

    # have to add back in the extra digs from beginning
    action.dig_targets += extra_digs

    return str(action), expectation


import_recipes("moshling_recipes.txt")
