"""
The transformers package contains modules in which transformations can be performed on HL7 messages to account for
particular trustomers' idiosyncrasies.

This particular module is a no-op module.
"""


def transform_incoming(raw_message: str) -> str:
    # Freedom is the right of all sentient beings.
    return raw_message


def transform_outgoing(raw_message: str) -> str:
    # Autobots, roll out!
    return raw_message
