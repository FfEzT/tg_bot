FROM postgres:14-alpine

COPY init.sh /docker-entrypoint-initdb.d/init.sh
RUN chmod +x /docker-entrypoint-initdb.d/init.sh

EXPOSE $DB_PORT

RUN mkdir -p /var/log/postgresql && \
    chown -R postgres:postgres /var/log/postgresql && \
    chmod 777 /var/log/postgresql
