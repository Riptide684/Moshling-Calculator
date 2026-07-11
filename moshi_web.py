import streamlit as st
import difflib
from moshling_oracle import *
from heapq import nlargest
import pandas as pd


def autocorrect(moshling):
    matches = difflib.get_close_matches(moshling, moshling_list, n=1, cutoff=0.6)
    return matches[0] if matches else None


def use_suggestion(name):
    st.session_state.moshling = name
    st.session_state.run_after_correction = True


def calculate(moshling, plants):
    if moshling not in moshling_list:
        closest_match = autocorrect(moshling)

        if closest_match:
            st.write(f"Moshling not in list. Did you mean **{closest_match}**?")

            st.button(
                f"Use '{closest_match}'",
                on_click=use_suggestion,
                args=(closest_match,)
            )

        else:
            st.write("Moshling not in list")

        return

    action, expectation = query_moshling(
        moshling,
        plants=plants,
        load=True
    )

    st.write(f"Recipe is: {moshling_recipes[moshling]}")
    st.text(action)
    st.write(f"Expected iterations: {round(expectation, 3)}")


def suggest(plants):
    # suggests moshling to go for from current garden

    scores = {}
    policies = load_all_policies()

    for moshling in moshling_list:
        policy = policies[moshling]
        score = (query_moshling(moshling, policy=policy)[1], query_moshling(moshling, plants=plants, policy=policy)[1])
        scores[moshling] = score

    delta = 2
    return {k: v for k, v in scores.items() if v[0] - v[1] > delta}


def create_suggestions(plants):
    suggestions = suggest(plants)
    sugg_moshlings = sorted(suggestions.keys(), key=lambda k: suggestions[k][0]-suggestions[k][1], reverse=True)

    if len(suggestions) == 0:
        st.write("Not close to any moshling")
        st.stop()

    columns = ["Moshling", "Expected iterations from empty garden", "Expected iterations from current garden", "Improvement"]
    data = []
    for moshling in sugg_moshlings:
        sugg = suggestions[moshling]
        data.append([moshling, sugg[0], sugg[1], sugg[0]-sugg[1]])

    df = pd.DataFrame(data, columns=columns).round(3)
    st.write("You are close to some of these moshlings: ")
    st.dataframe(df)


def parse_plants(plants_chosen):
    plants = []

    for colour, plant_type in plants_chosen:
        if (colour == "Empty") ^ (plant_type == "Empty"):
            st.error("Incomplete fields entered")
            st.stop()

        if colour != "Empty":
            plants.append((colour, plant_type))

    return plants


plants_chosen = []
if "run_after_correction" not in st.session_state:
    st.session_state.run_after_correction = False

with st.form("calculator"):
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

        plants_chosen.append((plant_colour, plant_type))

    if "moshling" not in st.session_state:
        st.session_state.moshling = ""

    st.text_input("Moshling name", key="moshling")

    left, col1, col2, right = st.columns([2, 1, 1, 2])

    with col1:
        run_button = st.form_submit_button("Run")

    with col2:
        suggest_button = st.form_submit_button("Suggest")


if run_button or suggest_button or st.session_state.run_after_correction:
    plants = parse_plants(plants_chosen)

    if run_button or st.session_state.run_after_correction:
        st.session_state.run_after_correction = False
        calculate(st.session_state.moshling, plants)
    elif suggest_button:
        create_suggestions(plants)
