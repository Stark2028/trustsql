"""Publish curated synthetic metadata through the official DataHub emitter.

Run in an optional ingestion environment with acryl-datahub installed.
Warehouse records are never sent; descriptions and schema only.
"""

import os
import sys

from trustsql.catalog import snapshot


def main():
    try:
        from datahub.emitter.mcp import MetadataChangeProposalWrapper
        from datahub.emitter.rest_emitter import DatahubRestEmitter
        from datahub.metadata.schema_classes import (
            DatasetPropertiesClass,
            NumberTypeClass,
            OtherSchemaClass,
            SchemaFieldClass,
            SchemaFieldDataTypeClass,
            SchemaMetadataClass,
            StringTypeClass,
        )
    except ImportError:
        sys.exit("Install the optional DataHub ingestion dependencies first. See docs/DATAHUB.md.")
    endpoint = os.environ.get("DATAHUB_GMS_URL")
    token = os.environ.get("TRUSTSQL_DATAHUB_TOKEN")
    if not endpoint:
        sys.exit("DATAHUB_GMS_URL is required. It is the GMS base URL, not the GraphQL URL.")
    emitter = DatahubRestEmitter(gms_server=endpoint, token=token)
    count = 0
    for dataset in snapshot():
        emitter.emit(
            MetadataChangeProposalWrapper(
                entityUrn=dataset.urn,
                aspect=DatasetPropertiesClass(
                    name=dataset.table,
                    description=dataset.description,
                    customProperties={
                        "trustsql.owner": dataset.owner,
                        "trustsql.certified": str(dataset.certified).lower(),
                        "trustsql.freshness": dataset.freshness,
                    },
                ),
            )
        )
        fields = [
            SchemaFieldClass(
                fieldPath=c.name,
                nativeDataType=c.type,
                description=c.description,
                type=SchemaFieldDataTypeClass(
                    type=NumberTypeClass() if c.type == "INTEGER" else StringTypeClass()
                ),
                nullable=False,
            )
            for c in dataset.columns
        ]
        emitter.emit(
            MetadataChangeProposalWrapper(
                entityUrn=dataset.urn,
                aspect=SchemaMetadataClass(
                    schemaName=f"analytics.{dataset.table}",
                    platform="urn:li:dataPlatform:postgres",
                    version=0,
                    hash="",
                    platformSchema=OtherSchemaClass(rawSchema=""),
                    fields=fields,
                ),
            )
        )
        count += 1
    print(
        f"Published schema and curated descriptions for {count} synthetic datasets. Verify readback in live mode."
    )


if __name__ == "__main__":
    main()
