Feature: ORU message processing

    Scenario: New ORU message is received and published to DHOS
        Given the Trustomer API is running
        And RabbitMQ is running
        And there exists a clinician
        And there exists a patient
        And there exists an encounter
        And there exists an observation set
        When an ORU message is sent
        And the message is retrieved by its MRN
        Then the ORU HL7 message contains patient data
    


        
