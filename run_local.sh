#!/bin/bash

SERVER_PORT=${1-5000}
export SERVER_PORT=${SERVER_PORT}
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_USER=dhos-connector-api
export DATABASE_PASSWORD=dhos-connector-api
export DATABASE_NAME=dhos-connector-api
export AUTH0_DOMAIN=https://login-sandbox.sensynehealth.com/
export AUTH0_AUDIENCE=https://dev.sensynehealth.com/
export AUTH0_METADATA=https://gdm.sensynehealth.com/metadata
export AUTH0_JWKS_URL=https://login-sandbox.sensynehealth.com/.well-known/jwks.json
export ENVIRONMENT=DEVELOPMENT
export ALLOW_DROP_DATA=true
export SERVER_TIMEZONE=UTC
export PROXY_URL=http://localhost
export HS_KEY=secret
export FLASK_APP=dhos_connector_api/autoapp.py
export RABBITMQ_DISABLED=True
export EPR_SERVICE_ADAPTER_HS_KEY=secretepr
export EPR_SERVICE_ADAPTER_ISSUER=http://epr/
export IGNORE_JWT_VALIDATION=True
export EPR_SERVICE_ADAPTER_URL_BASE=http://epr-service-adapter
export MIRTH_HOST_URL_BASE=http://mirth-test
export MIRTH_USERNAME=user1
export MIRTH_PASSWORD=password1
export TOKEN_URL=https://draysonhealth-sandbox.eu.auth0.com/oauth/token
export AUTH0_MGMT_CLIENT_ID=WnaASHW63XtaMbMdvooTGGevjSKjq3KJ
export AUTH0_MGMT_CLIENT_SECRET=1w_VzWhv1zutgGgVOw-TR7bdJF4t7zE3NIHXiQHnldoImQP9vJfd2jLhGoD4Dol8
export AUTH0_AUTHZ_CLIENT_ID=zzx3GTSQv9JRgNG97sdeDfpSp9D15cNK
export AUTH0_AUTHZ_CLIENT_SECRET=qHATW1Y3b4-Hbua6O7j2jCPSAnhqhzQLbrBGLivnAuE5HIy2HGIpSunj-kuMosQS
export AUTH0_AUTHZ_WEBTASK_URL=https://draysonhealth-sandbox.eu.webtask.io/adf6e2f2b84784b57522e3b19dfc9201/api
export AUTH0_CLIENT_ID=jpvbEJUhH3SFgZ6Kfd0E95QLFwP2d3nB
export NONCUSTOM_AUTH0_DOMAIN=https://draysonhealth-sandbox.eu.auth0.com
export CUSTOMER_CODE=DEV
export AUTH0_AUDIENCE=https://dev.sensynehealth.com
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=secret
export DHOS_TRUSTOMER_API_HOST=http://dhos-trustomer
export CUSTOMER_CODE=dev
export POLARIS_API_KEY=secret
export LOG_LEVEL=DEBUG
export LOG_FORMAT=${LOG_FORMAT:-COLOUR}

if [ -z "$*" ]
then
   flask db upgrade
   python -m dhos_connector_api
else
flask $*
fi
