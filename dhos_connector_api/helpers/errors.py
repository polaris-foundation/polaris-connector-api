from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper


class Hl7ApplicationRejectException(Exception):
    """
    An AR (Application Reject) message indicates one of two things: either there is a
    problem with field 9 (message type), field 11 (Processing ID) or field 12 (Version ID)
    of the MSH segment, or there is a problem with the receiving application that is not
    related to the message or its structure.
    """

    reason: str
    wrapped_message: Hl7Wrapper

    def __init__(self, reason: str, wrapped_message: Hl7Wrapper):
        self.reason = reason
        self.wrapped_message = wrapped_message


class Hl7ApplicationErrorException(Exception):
    """
    An AE (Application Error) message indicates that there was a problem processing the
    message. This could be related to the message structure, or the message itself. The
    ending application must correct this problem before attempting to resend the message.
    """

    reason: str
    wrapped_message: Hl7Wrapper

    def __init__(self, reason: str, wrapped_message: Hl7Wrapper):
        self.reason = reason
        self.wrapped_message = wrapped_message
