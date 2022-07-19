Feature: CDA message processing

    Scenario: New CDA message is received and forwarded to trust
        Given the Trustomer API is running
        And RabbitMQ is running
        And there exists a patient
        And there exists an encounter
        When a CDA message is sent
        Then the sent CDA message is received by the receiving system

    


        
