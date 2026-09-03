FROM postgres:16-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip curl \
    && pip3 install --break-system-packages "patroni[etcd3]==4.0.6" psycopg2-binary \
    && rm -rf /var/lib/apt/lists/*

COPY patroni.yml /etc/patroni.yml
COPY bootstrap.sh /usr/local/bin/bootstrap-patroni
COPY create_app_user.sh /usr/local/bin/create_app_user.sh
RUN chmod +x /usr/local/bin/bootstrap-patroni /usr/local/bin/create_app_user.sh

USER postgres
EXPOSE 5432 8008
ENTRYPOINT ["/usr/local/bin/bootstrap-patroni"]
