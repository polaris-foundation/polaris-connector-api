Feature: HL7 message is published to DHOS

    Background:
        Given the Trustomer API is running
        And RabbitMQ is running

    Scenario: Valid HL7 message is received and published to DHOS
        When a valid HL7 message is sent
        Then an internal message is published to RabbitMQ
        And the API responds with an AA ACK message
        And the message can be found by its uuid
        And the message can be found by its MRN
        And the message can be found by its Message Control ID
        
    Scenario: Duplicate HL7 message is received and published to DHOS
        And a valid HL7 message is sent
        And an internal message is published to RabbitMQ
        When a duplicate HL7 message is sent
        Then no internal message is published to RabbitMQ
        And the API responds with an AR ACK message
