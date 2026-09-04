#!/usr/bin/env python3
"""Build or read-only validate the frozen G1J Selector-Intent dataset."""

from rwkv_lh.goal_state_protocols.dataset_contract import generator_main


if __name__ == "__main__":
    generator_main("selector_intent")
