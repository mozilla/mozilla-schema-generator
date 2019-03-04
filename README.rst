=============================
Mozilla Schema Creator
=============================

.. image:: https://badge.fury.io/py/mozilla-schema-creator.png
    :target: http://badge.fury.io/py/mozilla-schema-creator

.. image:: https://travis-ci.org/fbertsch/mozilla-schema-creator.png?branch=master
    :target: https://travis-ci.org/fbertsch/mozilla-schema-creator

A library for creating full representations of Mozilla telemetry pings.

See [Mozilla Pipeline Schemas](https://www.github.com/mozilla-services/mozilla-pipeline-services)
for the more generic structure of pings. This library takes those generic structures and fills in
all of the probes we expect to see in the appropriate places.

## Telemetry Integration

There are two pings we are targeting for integration with this library:

1. [The Main Ping](http://gecko-docs.mozilla.org.s3.amazonaws.com/toolkit/components/telemetry/telemetry/data/main-ping.html)
   is the historical Firefox Desktop ping, and contains many more than ten-thousand total pieces of data.
2. [The Glean Ping](https://github.com/mozilla/glean_parser) is the new ping-type being created for
   more generic data collection.

This library takes the information for what should be in those pings from the [Probe Info Service](https://www.github.com/mozilla/probe-scraper).

## Data Store Integration

The primary use of the schemas is for integration with the
[Schema Transpiler](https://www.github.com/mozilla/jsonschema-transpiler). 
The schemas that this repository creates can be transpiled into Avro and Bigquery. They define
the schema of the Avro and BigQuery tables that the [BQ Sink](https://www.github.com/mozilla/gcp-ingestion)
writes to.

### BigQuery Limitations

BigQuery has a hard limit of ten thousand columns on any single table. This library
takes that limitation into account by splitting schemas into multiple tables. Each
table has some common information that are duplicated in every table, and then a set
of fields that are unique to that table. The join of these tables gives the full
set of fields available from the ping.

## Validation

A secondary use-case of these schemas is for validation. The schemas produced are guaranteed to
be more correct, since they include explicit definitions of every metric and probe.

## Development and Testing

Run tests:
```
make test
```

## Running

Create JSON files:
```
make run
```
