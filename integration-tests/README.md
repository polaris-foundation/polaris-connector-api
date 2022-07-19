# DHOS Connector API Integration Tests
Service-level integration tests for the DHOS Connector API.

## Running the tests
```
# build containers
$ docker-compose build

# run tests
$ docker-compose up --abort-on-container-exit --exit-code-from dhos-connector-integration-tests

# inspect test logs
$ docker logs dhos-connector-integration-tests

# cleanup
$ docker-compose down
```

## Test development
For test development purposes you can keep the service running and keep re-running only the tests:
```
# in one terminal screen, or add `-d` flag if you don't want the process running in foreground
$ docker-compose up --force-recreate

# in another terminal screen you can now run the tests
$ DHOS_CONNECTOR_API_HOST=http://localhost:5000 \
  EPR_SERVICE_ADAPTER_URL_BASE=http://localhost:8080 \
  RABBITMQ_HOST=localhost \
  HS_ISSUER=http://localhost/ \
  HS_KEY=secret \
  PROXY_URL=http://localhost \
  SYSTEM_JWT_SCOPE="read:hl7_message write:hl7_message" \
  behave --no-capture

# Don't forget to clean up when done!
$ docker-compose down
```
