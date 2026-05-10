#!/bin/bash

(cd prefect && docker compose up -d) &
(cd kafka && docker compose up -d) &
(cd ML && docker compose up -d) &
(cd elasticsearch && docker compose up -d) &
(cd dashboard && docker compose up -d) &

wait
echo "All services started 🚀"