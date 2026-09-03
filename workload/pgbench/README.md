# pgbench workload

Initialize a database through the HAProxy primary endpoint:

```bash
PGPASSWORD=app pgbench -h localhost -p 5432 -U app -i -s 10 citylab
```

Run a fixed-duration benchmark:

```bash
PGPASSWORD=app pgbench -h localhost -p 5432 -U app -c 50 -j 4 -T 300 -P 5 citylab | tee pgbench.log
```

Record PostgreSQL version, scale factor, client count, thread count, duration and host resources in the experiment metadata. Do not compare results across candidates unless the workload and resource normalization are documented.
