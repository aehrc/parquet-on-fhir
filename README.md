# Parquet on FHIR

This specification defines a method for representing FHIR data within
the [Apache Parquet](https://parquet.apache.org/) format.

Rather than defining a schema for each of the resource types within FHIR, it
defines a method for deriving a schema from a resource definition.

This format is intended to be a lossless representation of FHIR. For example,
FHIR JSON converted to this format should be able to be regenerated from the
format without any loss of data.

The format is intended to define the structure and types of the schema without
requiring all fields to be present. A data set that populates only a few
elements for a resource can be represented by a schema with only those fields in
the Parquet schema.

It is the intent that multiple Parquet tables could exist for the same resource
that have different fields in their schemas, and that these schemas could be
merged to produce a single table with the union of those fields.

## Resource type

The schema for a Parquet table SHALL be derived from a single base FHIR resource
definition.

The schema SHALL contain a field named `resourceType` with a primitive type
of `binary` and a logical type of `STRING`, and it SHALL be set to a type from
the FHIR resource types value
set ([http://hl7.org/fhir/ValueSet/resource-types](http://hl7.org/fhir/ValueSet/resource-types)).

All rows within the table SHALL contain the same value for the "resourceType"
field.

## Field optionality

The only field that must be present within the table is the `resourceType`
field. It MUST always be in the schema of any table that complies with this
specification, and also marked as required within the schema.

All other fields can be optionally included in the schema as needed to represent
the data set. Consuming applications SHALL be able to tolerate the absence of
any field within the schema except for `resourceType`.

All fields in the schema other than the `resourceType` field SHALL be marked as
optional.

## Primitive elements

The value of each primitive element within a resource definition is represented
as a field within the schema with the same name.

The
Parquet [primitive](https://github.com/apache/parquet-format/blob/master/Encodings.md)
and [logical types](https://github.com/apache/parquet-format/blob/master/LogicalTypes.md)
of the value field SHALL be determined by the element type according to the
following table:

| FHIR type    | Parquet primitive type | Parquet logical type |
|--------------|------------------------|----------------------|
| base64Binary | binary                 |                      |
| boolean      | boolean                |                      |
| canonical    | binary                 | STRING               |
| code         | binary                 | STRING               |
| date         | binary                 | STRING               |
| dateTime     | binary                 | STRING               |
| decimal      | binary                 | STRING               |
| id           | binary                 | STRING               |
| instant      | binary                 | STRING               |
| integer      | INT32                  | INT(32, true)        |
| integer64    | INT64                  | INT(64, true)        |
| markdown     | binary                 | STRING               |
| oid          | binary                 | STRING               |
| positiveInt  | INT32                  | INT(32, false)       |
| string       | binary                 | STRING               |
| time         | binary                 | STRING               |
| unsignedInt  | INT32                  | INT(32, false)       |
| uri          | binary                 | STRING               |
| url          | binary                 | STRING               |
| uuid         | binary                 | STRING               |

The format of the data stored within each field SHALL comply with the rules
defined in the [Data Types](https://hl7.org/fhir/datatypes.html) section of the
FHIR specification.

Here is an example of a simple Patient resource:

```json
{
  "resourceType": "Patient",
  "id": "example",
  "birthDate": "1970-01-01"
}
```

This example could be accommodated within the following schema:

```
message Patient {
  required binary resourceType (STRING);
  optional binary id (STRING);
  optional binary birthDate (STRING);
}
```

## Repeating elements

Any element that has a maximum cardinality greater than one (1) SHALL be
represented as a group containing a repeated list field.

Here is an example of a repeating element within the AllergyIntolerance
resource:

```json
{
  "resourceType": "AllergyIntolerance",
  "category": [
    "food",
    "environment"
  ]
}
```

This example could be accommodated within the following schema:

```
message AllergyIntolerance {
  required binary resourceType (STRING);
  optional group category (LIST) {
    repeated group list {
      optional binary element (STRING);
    }
  }
}
```

## Choice types

If an element has a choice type (i.e. it can have more than one data type), it
SHALL be represented as with a field for each of its valid types.

The name of each field SHALL follow the format `value[type]`, where `[type]` is
the name of the type in upper camel case.

Here is an example of an element with a choice type in two different Patient
resource:

```json
{
  "resourceType": "Patient",
  "multipleBirthBoolean": false
}
```

```json
{
  "resourceType": "Patient",
  "multipleBirthInteger": 2
}
```

These examples could be accommodated within the following schema:

```
message Patient {
  required binary resourceType (STRING);
  optional boolean multipleBirthBoolean;
  optional int32 multipleBirthInteger (INT(32, true));
}
```

## Complex and backbone elements

Each complex and backbone element within a resource definition SHALL be
represented as a group within the schema with the same name. The group SHALL
contain a field for each of the child elements.

Here is an example of a Reference element within the Condition resource:

```json
{
  "resourceType": "Condition",
  "subject": {
    "reference": "Patient/123"
  }
}
```

This example could be accommodated within the following schema:

```
message Condition {
  required binary resourceType (STRING);
  optional group subject {
    optional binary reference (STRING);
  }
}
```

## Extensions

Extensions at the resource level and within complex elements SHALL be
represented as a group within the schema with the name `extension`.

The `extension` group SHALL contain fields for each of the elements within
the [Extension](https://hl7.org/fhir/extensibility.html#Extension) data type, as
per the rules in
the [Complex and backbone elements](#complex-and-backbone-elements) section.

Here is an example of a Patient resource with an extension at the root level:

```json
{
  "resourceType": "Patient",
  "extension": [
    {
      "url": "http://hl7.org.au/fhir/StructureDefinition/indigenous-status",
      "valueCoding": {
        "system": "https://healthterminologies.gov.au/fhir/CodeSystem/australian-indigenous-status-1",
        "code": "1",
        "display": "Aboriginal but not Torres Strait Islander origin"
      }
    }
  ]
}
```

This example could be accommodated within the following schema:

```
message Patient {
  required binary resourceType (STRING);
  optional group extension (LIST) {
    repeated group list {
      optional group element {
        optional binary url (STRING);
        optional group valueCoding {
          optional binary code (STRING);
          optional binary display (STRING);
          optional binary system (STRING);
        }
      }
    }
  }
}
```

### Primitive extensions and internal identifiers

Extensions and the internal identifier of each primitive element can be
represented within the schema as a field within the schema with the same name
prepended with an underscore.

This field is represented as a group within the schema that can contain the
following fields:

| Field name | Parquet primitive type | Parquet logical type                                                                             |
|------------|------------------------|--------------------------------------------------------------------------------------------------|
| id         | binary                 | STRING                                                                                           |
| extension  | group                  | As per the Extension data type ([Complex and backbone elements](#complex-and-backbone-elements)) |

Here is an example of a Patient resource with a primitive element that has
an `id` and an extension:

```json
{
  "resourceType": "Patient",
  "birthDate": "1970-01-01",
  "_birthDate": {
    "id": "1",
    "extension": [
      {
        "url": "http://hl7.org/fhir/StructureDefinition/patient-birthTime",
        "valueDateTime": "1970-01-01T00:00:00Z"
      }
    ]
  }
}
```

This example could be accommodated within the following schema:

```
message Patient {
  required binary resourceType (STRING);
  optional binary birthDate (STRING);
  optional group _birthDate {
    optional binary id (STRING);
    optional group extension {
      optional binary url (STRING);
      optional binary valueDateTime (STRING);
    }
  }
}
```

## Annotations

Annotations are a mechanism for including derived forms of element values that
may be useful for querying the data.

An annotated field is the name of the annotated element, prefixed by two
underscores (`__`) and suffixed by an underscore and the name of the
annotation (`_[annotation name]`).

Each annotation defined in this specification provides a name and a description
of the data type or schema for that field.

Non-standard annotations can be included in the format provided that their names
do not collide with the annotations defined in this specification.

### Date ranges

Any element with the `date` or `dateTime` data type can be annotated with range
annotations.

The `start` annotation describes the earliest instant that is considered to be
included in the value.

The `end` annotation describes the latest instant that is considered to be
included in the value.

For example, a value of `2014-06-01T12:05Z` would have a start
of `2014-06-01T12:05:00.000Z` and an end of `2014-06-01T12:05:59.999Z` at
millisecond precision.

Both the `start` and `end` annotations use the `int96` Parquet primitive type,
and the `TIMESTAMP(isAdjustedToUTC=true, unit=MILLIS)` logical type.

Here is an example of a schema that can accommodate Patient resources with
the `birthDate` element populated, along with annotation fields to store the
range.

```
message Patient {
  required binary resourceType (STRING);
  optional binary birthDate (STRING);
  optional int96 __birthDate_start (TIMESTAMP(isAdjustedToUTC=true, unit=MILLIS));
  optional int96 __birthDate_end (TIMESTAMP(isAdjustedToUTC=true, unit=MILLIS));
```

### Decimal values

The original values of decimals are stored as strings to preserve the precision
and scale of the original data.

Elements with a decimal type can use the `numeric` to store the value in a
numeric form.

The `numeric` annotation uses the `fixed_len_byte_array(16)` Parquet primitive
type, and the `DECIMAL(precision=38, scale=6)` logical type.

Here is an example of a schema that can accommodate Observation resources with
an annotated decimal value:

```
message Observation {
  required binary resourceType (STRING);
  optional binary valueDecimal (STRING);
  optional fixed_len_byte_array(16) __valueDecimal_numeric (DECIMAL(precision=38, scale=6));
}
```

### Quantity unit canonicalization

Elements of type Quantity can be annotated with the `canonical` annotation to
add canonical unit and value information. This can assist with comparison of
Quantity values at query time.

For example, temperature observations in Celsius or Fahrenheit could be
canonicalized to Kelvin.

The `canonical` annotation is represented as a group within the schema that can
contain the following fields:

| Field name | Parquet primitive type   | Parquet logical type           |
|------------|--------------------------|--------------------------------|
| value      | fixed_len_byte_array(16) | DECIMAL(precision=38, scale=6) |
| code       | binary                   | STRING                         |

## Examples

### Patient

Here is an example of a Patient resource:

```json
{
  "resourceType": "Patient",
  "id": "bennelong-anne",
  "meta": {
    "profile": [
      "http://hl7.org.au/fhir/core/StructureDefinition/au-core-patient"
    ]
  },
  "text": {
    "status": "generated",
    "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\"><p class=\"res-header-id\"><b>Generated Narrative: Patient bennelong-anne</b></p><a name=\"bennelong-anne\"> </a><a name=\"hcbennelong-anne\"> </a><a name=\"hcbennelong-anne-en-AU\"> </a><p style=\"border: 1px #661aff solid; background-color: #e6e6ff; padding: 10px;\">Mrs. Anne Mary Bennelong(official) Female, DoB: 1968-10-11 ( Medicare Number:\u00a06951449677)</p><hr/><table class=\"grid\"><tr><td style=\"background-color: #f3f5da\" title=\"Ways to contact the Patient\">Contact Detail</td><td colspan=\"3\"><ul><li>ph: 0491 572 665(Mobile)</li><li>4 Brisbane Street Brisbane QLD 4112 AU (home)</li></ul></td></tr><tr><td style=\"background-color: #f3f5da\" title=\"Language spoken\">Language:</td><td colspan=\"3\"><span title=\"Codes:{urn:ietf:bcp:47 yub}\">Yugambal</span></td></tr><tr><td style=\"background-color: #f3f5da\" title=\"This extension applies to the Patient, Person, and RelatedPerson resources and is used to indicate whether a person identifies as being of Aboriginal or Torres Strait Islander origin.\"><a href=\"https://build.fhir.org/ig/hl7au/au-fhir-base/StructureDefinition-indigenous-status.html\">Australian Indigenous Status</a></td><td colspan=\"3\">australian-indigenous-status-1 1: Aboriginal but not Torres Strait Islander origin</td></tr></table></div>"
  },
  "extension": [
    {
      "url": "http://hl7.org.au/fhir/StructureDefinition/indigenous-status",
      "valueCoding": {
        "system": "https://healthterminologies.gov.au/fhir/CodeSystem/australian-indigenous-status-1",
        "code": "1",
        "display": "Aboriginal but not Torres Strait Islander origin"
      }
    }
  ],
  "identifier": [
    {
      "type": {
        "coding": [
          {
            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
            "code": "MC"
          }
        ],
        "text": "Medicare Number"
      },
      "system": "http://ns.electronichealth.net.au/id/medicare-number",
      "value": "6951449677"
    }
  ],
  "name": [
    {
      "use": "official",
      "text": "Mrs. Anne Mary Bennelong",
      "family": "Bennelong",
      "given": [
        "Anne"
      ],
      "prefix": [
        "Mrs"
      ]
    }
  ],
  "telecom": [
    {
      "system": "phone",
      "value": "0491 572 665",
      "use": "mobile"
    }
  ],
  "gender": "female",
  "birthDate": "1968-10-11",
  "address": [
    {
      "use": "home",
      "line": [
        "4 Brisbane Street"
      ],
      "city": "Brisbane",
      "state": "QLD",
      "postalCode": "4112",
      "country": "AU"
    }
  ],
  "communication": [
    {
      "language": {
        "coding": [
          {
            "system": "urn:ietf:bcp:47",
            "code": "yub"
          }
        ],
        "text": "Yugambal"
      }
    }
  ]
}
```

This is a Parquet schema that complies with this specification and can
accommodate the example Patient resource:

```
message Patient {
  required binary resourceType (STRING);
  optional binary id (STRING);
  optional group meta {
    optional group profile (LIST) {
      repeated group list {
        optional binary element (STRING);
      }
    }
  }
  optional group text {
    optional binary div (STRING);
    optional binary status (STRING);
  }
  optional group extension (LIST) {
    repeated group list {
      optional group element {
        optional binary url (STRING);
        optional group valueCoding {
          optional binary code (STRING);
          optional binary display (STRING);
          optional binary system (STRING);
        }
      }
    }
  }
  optional group identifier (LIST) {
    repeated group list {
      optional group element {
        optional binary system (STRING);
        optional group type {
          optional group coding (LIST) {
            repeated group list {
              optional group element {
                optional binary code (STRING);
                optional binary system (STRING);
              }
            }
          }
          optional binary text (STRING);
        }
        optional binary value (STRING);
      }
    }
  }
  optional group name (LIST) {
    repeated group list {
      optional group element {
        optional binary family (STRING);
        optional group given (LIST) {
          repeated group list {
            optional binary element (STRING);
          }
        }
        optional group prefix (LIST) {
          repeated group list {
            optional binary element (STRING);
          }
        }
        optional binary text (STRING);
        optional binary use (STRING);
      }
    }
  }
  optional group telecom (LIST) {
    repeated group list {
      optional group element {
        optional binary system (STRING);
        optional binary use (STRING);
        optional binary value (STRING);
      }
    }
  }
  optional binary gender (STRING);
  optional binary birthDate (STRING);
  optional int96 __birthDate_start (TIMESTAMP(isAdjustedToUTC=true, unit=MILLIS));
  optional int96 __birthDate_end (TIMESTAMP(isAdjustedToUTC=true, unit=MILLIS));
  optional group address (LIST) {
    repeated group list {
      optional group element {
        optional binary city (STRING);
        optional binary country (STRING);
        optional group line (LIST) {
          repeated group list {
            optional binary element (STRING);
          }
        }
        optional binary postalCode (STRING);
        optional binary state (STRING);
        optional binary use (STRING);
      }
    }
  }
  optional group communication (LIST) {
    repeated group list {
      optional group element {
        optional group language {
          optional group coding (LIST) {
            repeated group list {
              optional group element {
                optional binary code (STRING);
                optional binary system (STRING);
              }
            }
          }
          optional binary text (STRING);
        }
      }
    }
  }
}
```

### Observation

Here is an example of an Observation resource:

```json
{
  "resourceType": "Observation",
  "id": "bodytemp-1",
  "meta": {
    "profile": [
      "http://hl7.org.au/fhir/core/StructureDefinition/au-core-bodytemp"
    ]
  },
  "text": {
    "status": "generated",
    "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\"><p class=\"res-header-id\"><b>Generated Narrative: Observation bodytemp-1</b></p><a name=\"bodytemp-1\"> </a><a name=\"hcbodytemp-1\"> </a><a name=\"hcbodytemp-1-en-AU\"> </a><p><b>status</b>: Final</p><p><b>category</b>: <span title=\"Codes:{http://terminology.hl7.org/CodeSystem/observation-category vital-signs}\">Vital Signs</span></p><p><b>code</b>: <span title=\"Codes:{http://loinc.org 8310-5}, {http://snomed.info/sct 386725007}\">Body temperature</span></p><p><b>subject</b>: <a href=\"Patient-bennelong-anne.html\">Mrs. Anne Mary Bennelong(official) Female, DoB: 1968-10-11 ( Medicare Number:\u00a06951449677)</a></p><p><b>effective</b>: 2022-02-10</p><p><b>value</b>: 36.5 C<span style=\"background: LightGoldenRodYellow\"> (Details: UCUM  codeCel = 'Cel')</span></p></div>"
  },
  "status": "final",
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/observation-category",
          "code": "vital-signs",
          "display": "Vital Signs"
        }
      ],
      "text": "Vital Signs"
    }
  ],
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "8310-5",
        "display": "Body temperature"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "386725007"
      }
    ],
    "text": "Body temperature"
  },
  "subject": {
    "reference": "Patient/bennelong-anne"
  },
  "effectiveDateTime": "2022-02-10",
  "valueQuantity": {
    "value": 36.5,
    "unit": "C",
    "system": "http://unitsofmeasure.org",
    "code": "Cel"
  }
}
```

This is a Parquet schema that complies with this specification and can
accommodate the example Observation resource:

```
message Observation {
  required binary resourceType (STRING);
  optional binary id (STRING);
  optional group meta {
    optional group profile (LIST) {
      repeated group list {
        optional binary element (STRING);
      }
    }
  }
  optional group text {
    optional binary div (STRING);
    optional binary status (STRING);
  }
  optional binary status (STRING);
  optional group category (LIST) {
    repeated group list {
      optional group element {
        optional group coding (LIST) {
          repeated group list {
            optional group element {
              optional binary code (STRING);
              optional binary display (STRING);
              optional binary system (STRING);
            }
          }
        }
        optional binary text (STRING);
      }
    }
  }
  optional group code {
    optional group coding (LIST) {
      repeated group list {
        optional group element {
          optional binary code (STRING);
          optional binary display (STRING);
          optional binary system (STRING);
        }
      }
    }
    optional binary text (STRING);
  }
  optional group subject {
    optional binary reference (STRING);
  }
  optional binary effectiveDateTime (STRING);
  optional int96 __effectiveDateTime_start (TIMESTAMP(isAdjustedToUTC=true, unit=MILLIS));
  optional int96 __effectiveDateTime_end (TIMESTAMP(isAdjustedToUTC=true, unit=MILLIS));
  optional group valueQuantity {
    optional binary code (STRING);
    optional binary system (STRING);
    optional binary unit (STRING);
    optional binary value (STRING);
    optional fixed_len_byte_array(16) __value_numeric (DECIMAL(precision=38, scale=6));
  }
  optional group __valueQuantity_canonical {
    optional binary code (STRING);
    optional binary system (STRING);
    optional binary unit (STRING);
    optional binary value (STRING);
    optional fixed_len_byte_array(16) __value_numeric (DECIMAL(precision=38, scale=6));
  }
}
```
