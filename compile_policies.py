from moshling_oracle import *


if __name__ == '__main__':
    policies = {}

    for moshling in moshling_list:
        set_globals(moshling)
        policy = calculate_optimal_policy(moshling)
        policies[moshling] = policy.policy_actions
        
    with open('policies.pkl', 'wb') as f:
        pickle.dump(policies, f)