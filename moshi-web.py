from itertools import *
import numpy as np
from collections import Counter
import streamlit as st
import difflib


PLANT_TYPES = ("Love", "Pepper", "Orchid", "Apple", "Magic", "Frozen", "Star", "Dragon", "Daisy")

PLANT_COLOURS = ("Red", "Orange", "Yellow", "Green", "Blue", "Black", "Pink", "Purple")

moshling_recipes = {} # add from file

moshling_list = []

# individual plants are stored as integers from 0 to 72
# a garden is a sorted tuple of 3 of these integers

def plant_to_number(plant_colour, plant_type):
    # given text for a plant eg Red, Daisy returns the encoded plant number
    # the encoded plant number is between 1 and 72 (0 is reserved for the empty plant)
    return 1 + 8*PLANT_TYPES.index(plant_type) + PLANT_COLOURS.index(plant_colour)


def plant_numbers_to_number(plant_colour_number, plant_type_number):
    return 1 + 8*plant_type_number + plant_colour_number


def get_plant_type(plant_number):
    return PLANT_TYPES[(plant_number - 1) // 8]


def get_plant_colour(plant_number):
    return PLANT_COLOURS[(plant_number - 1 ) % 8]


def number_to_plant(plant_number):
    # reverses the above function
    if plant_number == 0:
        return "***"
    
    return get_plant_colour(plant_number) + " " + get_plant_type(plant_number)


def plants_to_garden(plants):
    # input of form [["Red","Daisy"],...] of length <= 3
    plant_numbers = [plant_to_number(*plant) for plant in plants] + [0] * (3 - len(plants))
    plant_numbers.sort()
    return tuple(plant_numbers)


def print_garden(garden):
    # prints the text for the garden tuple
    print(", ".join([number_to_plant(plant) for plant in garden]))


class Recipe:
    # recipe is stored as an array of 3 closed intervals represented by arrays of length 2
    def __init__(self, plant_texts):
        self.plants = []
        self.plant_types = []
        for plant_text in plant_texts:
            colour = plant_text.split(",")[0]
            ptype = plant_text.split(",")[1]

            if colour == "Any":
                self.plants.append([plant_to_number(PLANT_COLOURS[0], ptype), plant_to_number(PLANT_COLOURS[-1], ptype)])
            else:
                self.plants.append([plant_to_number(colour,ptype)]*2)

            self.plant_types.append(PLANT_TYPES.index(ptype))


    def __str__(self):
        text = []
        for plant in self.plants:
            if plant[0] == plant[1]:
                text.append(number_to_plant(plant[0]))
            else:
                text.append("Any " + get_plant_type(plant[0]))

        return ", ".join(text)
    

    def match(self, garden):
        # returns whether the given garden matches the recipe
        for perm in permutations(garden):
            for i in range(3):
                interval = self.plants[i]
                plant_number = perm[i]
                if not interval[0] <= plant_number <= interval[1]:
                    break
            else:
                return True
            
        return False


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
    if "***" in garden:
        return []
    
    matches = []
    
    for moshling in moshling_recipes:
        recipe = moshling_recipes[moshling]
        if recipe.match(garden):
            matches.append(moshling)

    return matches


def potential_moshlings(seeds):
    seeds = Counter([PLANT_TYPES.index(seed) for seed in seeds])
    matches = []
    for moshling in moshling_recipes:
        recipe = moshling_recipes[moshling]
        if seeds == Counter(recipe.plant_types):
            matches.append(moshling)

    return matches


def get_plants(moshling):
    # returns all coloured plants which appear in similar recipes
    all_plants = set()

    for potential in potential_moshlings([PLANT_TYPES[x] for x in moshling_recipes[moshling].plant_types]):
        recipe = moshling_recipes[potential]
        for interval in recipe.plants:
            if interval[0] == interval[1]:
                all_plants.add(interval[0])

    return list(all_plants)
    

class Action:
    # an action is digging up plants and then planting seeds
    def __init__(self, dig_targets, seeds):
        # dig_targets should be a tuple of plant numbers
        # seeds is an array of integers from 0 to 8 representing plant types
        self.dig_targets = dig_targets
        self.seeds = seeds

    def __str__(self):
        text = "Dig: " + ", ".join(number_to_plant(plant) for plant in self.dig_targets) 
        text = text + "\nPlant: " + ", ".join(PLANT_TYPES[seed] for seed in self.seeds)
        return text


def enumerate_gardens(restricted_plant_types):
    # returns a dictionary (initialised with None) with every possible state as a key
    # there are n <= 3 different plant types and 8 colours so 8n <= 24 distinct plants (8n+1 including the empty plant)
    # this gives (8n+3 choose 3) <= 2925 possible garden states (order doens't matter)
    possible_gardens = []
    # note that gardens must be sorted so restricted_plant_types must be sorted
    restricted_plant_types.sort()
    possible_plants = [0] + [plant_numbers_to_number(colour, type) for type in restricted_plant_types for colour in range(8)]
    l = len(possible_plants)

    for x in range(l):
        for y in range(x, l):
            for z in range(y, l):
                garden = tuple(possible_plants[_] for _ in [x,y,z])
                possible_gardens.append(garden)

    return possible_gardens


def enumerate_good_gardens(moshling):
    # returns all gardens which attract the given moshling
    recipe = moshling_recipes[moshling]
    plant_ranges = [[i for i in range(plant[0], plant[1] + 1)] for plant in recipe.plants]
    good_gardens = product(*[plant_ranges[i] for i in range(3)])

    ggs = set()
    for gg in good_gardens:
        ggs.add(tuple(sorted(gg)))

    return ggs


def enumerate_actions(garden, moshling):
    possible_actions = []
    res_plant_types = list(set(moshling_recipes[moshling].plant_types))

    # if we have matched any moshling then have to dig everything
    possible_dig_targets = []

    matched = moshling_match(garden)
    if matched:
        if moshling in matched:
            return [Action(tuple(plant for plant in garden if plant), moshling_recipes[moshling].plant_types)]
        else:
            possible_dig_targets = [[], [], [], [tuple(plant for plant in garden if plant)]]
    else:
        plants = [plant for plant in garden if plant]
        possible_dig_targets = [list(set(combinations(plants, r))) for r in range(4)]

    # plant some seeds for each set of digs
    for num_digs in range(4):
        num_empty = garden.count(0) + num_digs
        for num_seeds in range(1, num_empty + 1):
            possible_seeds = combinations_with_replacement(res_plant_types, num_seeds)
            possible_actions = possible_actions + [Action(x[0], x[1]) for x in product(possible_dig_targets[num_digs], possible_seeds)]

    return possible_actions


class Policy:
    # a policy is just a transition matrix once we have fixed the actions
    def __init__(self, restricted_plant_types):
        self.gardens = enumerate_gardens(restricted_plant_types)
        self.policy_actions = {}
        self.transitions = np.zeros((len(self.gardens), len(self.gardens)))
        self.garden_to_index = {
            garden: i
            for i, garden in enumerate(self.gardens)
        }
        self.expectations = None

    def default_populate(self, recipe):
        # creates the default action to try and get the given recipe (one shot attempt + digging everything)
        seeds = recipe.plant_types
        for garden in self.gardens:
            self.policy_actions[garden] = Action(tuple(plant for plant in garden if plant), seeds)

    
    def get_probabilities(self, garden, action):
        probabilities = np.zeros(self.transitions.shape[0])
        probs = {}
        num_seeds = len(action.seeds)
        num_empty = garden.count(0) + len(action.dig_targets) - num_seeds
        # removes any one copy of the specified plants
        base_plants = [plant for plant in garden if plant]
        
        for dig_target in action.dig_targets:
            base_plants.remove(dig_target)

        for colours in product(range(8), repeat=num_seeds):
            # plants all of the seeds and gives them the colour which is being looped over
            new_plants = base_plants + [plant_numbers_to_number(colours[i], action.seeds[i]) for i in range(num_seeds)]
            new_plants.sort()
            new_plants = ([0] * num_empty) + new_plants
            end = tuple(new_plants)

            probs[end] = probs.get(end, 0) + 1

        for end, count in probs.items():
            j = self.garden_to_index[end]
            probabilities[j] = count / (8 ** len(action.seeds))

        return probabilities


    def form_matrix(self):
        # fills out the transition matrix according to the policy actions
        self.transitions = np.zeros((len(self.gardens), len(self.gardens)))

        for garden in self.gardens:
            i = self.garden_to_index[garden]
            action = self.policy_actions[garden]
            self.transitions[i] = self.get_probabilities(garden, action)


    def modify_transitions(self, good_gardens):
        # removes absorbing states from the transition matrix

        P = self.transitions.copy() 
        P = np.delete(P, good_gardens, 0)
        P = np.delete(P, good_gardens, 1)

        return P


    def evaluate(self, good_gardens):
        # assume that expected hitting time from each state is finite

        # firstly need to remove the absorbing states from the matrix
        P = self.modify_transitions(good_gardens)

        # now solve (I-P)h = 1
        n = P.shape[0]
        h = np.linalg.solve(np.eye(n) - P, np.ones(n))
        self.expectations = h

        return h
    

    def export_policy(self):
        def pack_action(action):
            return ",".join(map(str, action.dig_targets)) + ";" + ",".join(map(str, action.seeds))
        
        def pack_garden(garden):
            return ",".join(map(str, garden))
        
        packed_text = []
        for garden in self.gardens:
            packed_text.append(pack_garden(garden) + ":" + pack_action(self.policy_actions[garden]))

        return "/".join(packed_text)

    
    def import_policy(self, packed_text):
        for block in packed_text.split("/"):
            garden_text = block.split(":")[0]
            dig_text, plant_text = block.split(":")[1].split(";")
            garden = tuple(map(int, garden_text.split(",")))
            if dig_text:
                dig_targets = tuple(map(int, dig_text.split(",")))
            else:
                dig_targets = ()
            seeds = list(map(int, plant_text.split(",")))
            self.policy_actions[garden] = Action(dig_targets, seeds)

        # need to recalculate transition matrix
        self.form_matrix()


def calculate_optimal_policy(moshling, verbose=False):
    recipe = moshling_recipes[moshling]
    restricted_plant_types = list(set(recipe.plant_types))

    # initial policy needs to be proper, for example just planting all of the required plants immediately and then digging everything
    policy = Policy(restricted_plant_types)
    good_gardens = [policy.garden_to_index[gg] for gg in enumerate_good_gardens(moshling)]
    policy.default_populate(moshling_recipes[moshling])
    policy.form_matrix()

    # now begin the process of evaluating and improving until we reach convergence
    iterations = 0
    max_iterations = 10
    stable = False
    stopping_parameter = 10e-8
    values = policy.evaluate(good_gardens)

    while not stable and iterations < max_iterations:
        new_actions = {}

        for garden in policy.gardens:
            best_q_value = 10e8
            best_action = None
            for action in enumerate_actions(garden, moshling):
                probabilities = np.delete(policy.get_probabilities(garden, action), good_gardens, 0)
                q_value = sum([probabilities[i] * values[i] for i in range(len(probabilities))])
                if q_value < best_q_value:
                    best_q_value = q_value
                    best_action = action

            if best_action == None:
                raise Exception("NO ACTION FOUND")
    
            new_actions[garden] = best_action

        policy.policy_actions = new_actions
        policy.form_matrix()
        new_values = policy.evaluate(good_gardens)

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
        print("Expected Time: " + str(policy.expectations[0]))

    return policy


def calculate_all_moshling_policies(filename):
    for moshling in moshling_recipes:
        print("Computing combinations for: " + moshling)
        policy = calculate_optimal_policy(moshling)
        packed_text = policy.export_policy()
        with open(filename, "a") as f:
            f.write(packed_text + "\n")


def import_moshling_policy(moshling):
    line_num = moshling_list.index(moshling)
    with open("moshling_policies.txt", "r") as f:
        for i, line in enumerate(f):
            if i == line_num:
                packed_text = line
                break

    policy = Policy(list(set(plant for plant in moshling_recipes[moshling].plant_types)))
    policy.import_policy(packed_text)
    # recalculates the expected hitting times
    good_gardens = [policy.garden_to_index[gg] for gg in enumerate_good_gardens(moshling)]
    policy.evaluate(good_gardens)

    return policy


def query_moshling(moshling, plants=[]):
    # firstly have to dig irrelevant plants
    garden = plants_to_garden(plants)
    res = list(set(moshling_recipes[moshling].plant_types))
    extra_digs = tuple(plant for plant in garden if plant and (plant - 1) // 8 not in res)
    garden = tuple(sorted(plant if (plant - 1) // 8 in res else 0 for plant in garden))

    policy = import_moshling_policy(moshling)

    # need to reindex in order to get expected hitting time
    good_gardens = [policy.garden_to_index[gg] for gg in enumerate_good_gardens(moshling)]
    starting_index = policy.garden_to_index[garden]
    if starting_index in good_gardens:
        expectation = 0
        action = Action([], [])
    else:
        garden_index = starting_index - sum([gg < starting_index for gg in good_gardens])
        expectation = policy.expectations[garden_index]
        action = policy.policy_actions[garden]

    # have to add back in the extra digs from beginning
    action.dig_targets += extra_digs

    return str(action), expectation


def autocorrect(moshling):
    matches = difflib.get_close_matches(moshling, moshling_list, n=1, cutoff=0.6)
    return matches[0] if matches else None


if __name__ == "__main__":
    import_recipes("moshling_recipes.txt")
    # fastest speedup is probably trying to limit how many colours needed by doing a preliminary search
    # can also remove certain actions which you would never do
    # the only reason you would leave empty is if planting extra could give an unwanted moshling
    # currently don't use the fact that you could get rarer moshlings, like Oddie vs Snookums
    # calculate_all_moshling_policies("moshling_policies.txt")
    # only very few coloured plants actually appear, so can reduce number of states massively
    
    plants_chosen = []

    for i in range(3):
        col1, col2 = st.columns(2)

        with col1:
            plant_type = st.selectbox(
                f"Plant {i + 1}",
                ("Empty",) + PLANT_TYPES,
                key=f"type_{i}",
            )

        with col2:
            plant_colour = st.selectbox(
                "Colour",
                ("Empty",) + PLANT_COLOURS,
                key=f"colour_{i}",
            )

        plants_chosen.append([plant_colour, plant_type])

    moshling = st.text_input("Moshling name")

    if st.button("Run"):
        plants = []
        for plant in plants_chosen:
            if (plant[0] == "Empty") ^ (plant[1] == "Empty"):
                st.text("Incomplete fields entered")
                st.stop()

            if plant[0] != "Empty" and plant[1] != "Empty":
                plants.append(plant)

        if moshling not in moshling_list:
            closest_match = autocorrect(moshling)
            if closest_match:
                st.text("Moshling not in list, did you mean: " + closest_match + "?")
            else:
                st.text("Moshling not in list")
            st.stop()
        
        action, expectation = query_moshling(moshling, plants)
        st.text("Recipe is: " + str(moshling_recipes[moshling]))
        st.text(action)
        st.text("Expected iterations: " + str(round(expectation, 3)))
