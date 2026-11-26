# Parquet on FHIR

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14166591.svg)](https://doi.org/10.5281/zenodo.14166591)

This specification defines a method for representing FHIR data within
the [Apache Parquet](https://parquet.apache.org/) format.

Rather than defining a schema for each of the resource types within FHIR, it
defines a method for deriving a schema from a resource definition.

This format is intended to be a lossless representation of FHIR. For example,
FHIR JSON converted to this format should be able to be regenerated from the
format without any loss of data.

The layout is a mapping
of [FHIR's JSON representation](https://hl7.org/fhir/R4/json.html) to Parquet.
Where this specification does not say otherwise, a field has the name, the
cardinality and the meaning that FHIR JSON gives it.

There is one exception to this mapping. A field at any level of the schema whose
name begins with two underscores (`__`) is a layout field, and is not FHIR
content. A conversion to FHIR SHALL leave out all layout fields. A consumer
SHALL ignore any layout field that it does not recognise. A producer MAY add
layout fields beyond those defined in this specification.
The [layout column](#layout-column) is a layout field, and the rules in that
section apply to it in place of the rule for unrecognised layout fields.

For example, a `_birthDate` group that contains an `id` of `b1` and the layout
fields `__start` and `__end` is converted to `"_birthDate": {"id": "b1"}` in
FHIR JSON.

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

Every table that complies with this specification SHALL contain the
`resourceType` field, marked as required within the schema, and the
[layout column](#layout-column).

All other fields can be optionally included in the schema as needed to
represent the data set. All fields other than `resourceType` SHALL be marked
as optional.

Consuming applications SHALL be able to tolerate the absence of any field
except `resourceType` and the layout column.

## Layout column

The layout column identifies a table as complying with this specification and
states its major version.

It SHALL be a field at the root of the schema named `__pof_v[n]` in lower
case, where `[n]` is the major version of this specification, written in
decimal without leading zeros. It SHALL have the `boolean` primitive type and
no logical type, SHALL be marked as optional, and every value SHALL be null.
For this version:

```
optional boolean __pof_v1;
```

A table SHALL contain exactly one layout column, unless a later release of
this specification defines otherwise.

The layout column is not an annotation and is not FHIR content. A producer
SHALL include it whether or not it includes any annotations. A conversion to a
FHIR format SHALL NOT emit it. A table without it, including the output of a
transformation that leaves it out, does not comply with this specification.

### Versions

The major version of this specification is raised only by a change that would
cause a consumer of the previous major version to misread complying data, such
as a change to the type, name or meaning of a field that version defines. Any
other change is released as a minor or patch version.

### Writing

A producer SHALL refuse to add data to a table if either the data or the table
lacks a layout column. It SHALL NOT add data of one major version to a table of
another, unless a later release of this specification defines them as
compatible.

### Reading

A consuming application SHALL recognise the layout column by its name and type
alone, without reading its values. A root field with a name of that form but a
type other than `boolean` is not a layout column.

- If the table has one layout column, of a version the application supports,
  the application SHALL read the table according to that version.
- If the version is one the application does not support, typically a higher
  one, the application SHALL refuse the table, and SHOULD report the version
  found and the versions it supports.
- If the table has more than one layout column, the application SHALL refuse
  it, unless a later release of this specification defines otherwise.
- If the table has no layout column, the application SHALL refuse it.

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
  optional boolean __pof_v1;
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
  optional boolean __pof_v1;
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
  optional boolean __pof_v1;
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
  optional boolean __pof_v1;
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
  optional boolean __pof_v1;
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
  optional boolean __pof_v1;
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

Where the primitive element repeats, this field follows FHIR JSON's
[representation of primitive elements](https://hl7.org/fhir/R4/json.html#primitive).
It is a list with the same length as the list of values, and the two lists are
aligned by position. An item is null where the value at the same position has
no `id`, no extensions and no [annotations](#annotations).

For example, here is a repeating element where only the second value has
an `id`:

```json
{
  "given": [
    "Anne",
    "Mary"
  ],
  "_given": [
    null,
    {
      "id": "g2"
    }
  ]
}
```

## Annotations

Annotations are a mechanism for including derived forms of element values that
may be useful for querying the data.

Each annotation is a layout field. It is stored within the container of the
element that it annotates, and its name is the name of the annotation prefixed
by two underscores (`__[annotation name]`).

The container depends on the type of the annotated element:

- A primitive element is annotated within the group that has the same name
  prepended with an underscore, as described
  in [Primitive extensions and internal identifiers](#primitive-extensions-and-internal-identifiers).
  For example, the `start` annotation of `birthDate` is `_birthDate.__start`.
  This group can contain annotations alone, with no `id` and no `extension`. In
  that case it has no FHIR content, and a conversion to FHIR leaves it out.
- A complex or backbone element is annotated within the group that represents
  it. For example, the `canonical_code` annotation of `valueQuantity`
  is `valueQuantity.__canonical_code`.

A primitive element within a complex element follows the first of these rules.
For example, the `numeric` annotation of the value of a quantity
is `valueQuantity._value.__numeric`.

Each annotation is a field of its own. The annotations of an element are not
grouped into a single structure. An annotation can have a group as its type
where its value has more than one part.

Each annotation defined in this specification provides a name and a description
of the data type or schema for that field.

Non-standard annotations can be included in the format provided that their names
do not collide with the annotations defined in this specification.

Names of the form `__pof_v[n]` are reserved for the
[layout column](#layout-column) and SHALL NOT be used for annotations or other
layout fields.

### Annotations on repeating elements

Where a complex or backbone element repeats, the annotations of each item are
fields of the group that represents that item.

Where a primitive element repeats, the field prepended with an underscore is a
list that is aligned by position with the list of values, as described
in [Primitive extensions and internal identifiers](#primitive-extensions-and-internal-identifiers).
The annotations of a value are fields of the item at the same position.

An item that contains annotations alone has no FHIR content. A conversion to
FHIR converts it to a null, which keeps the two lists aligned, and leaves out
the field where every item is null.

Here is an example of a MedicationRequest resource with a repeating element,
where only the first value has an `id`:

```json
{
  "resourceType": "MedicationRequest",
  "dosageInstruction": [
    {
      "timing": {
        "event": [
          "2024-03-01",
          "2024-03-02"
        ],
        "_event": [
          {
            "id": "e1"
          },
          null
        ]
      }
    }
  ]
}
```

This example could be accommodated within the following schema, along with
annotation fields to store the range of each value
(see [Date ranges](#date-ranges)):

```
message MedicationRequest {
  required binary resourceType (STRING);
  optional boolean __pof_v1;
  optional group dosageInstruction (LIST) {
    repeated group list {
      optional group element {
        optional group timing {
          optional group event (LIST) {
            repeated group list {
              optional binary element (STRING);
            }
          }
          optional group _event (LIST) {
            repeated group list {
              optional group element {
                optional binary id (STRING);
                optional int64 __start (TIMESTAMP(isAdjustedToUTC=true, unit=MICROS));
                optional int64 __end (TIMESTAMP(isAdjustedToUTC=true, unit=MICROS));
              }
            }
          }
        }
      }
    }
  }
}
```

When the range annotations are populated, neither item of `_event` is null. The
second item contains annotations alone, and a conversion to FHIR converts it to
the null shown in the example.

### Date ranges

Any element with the `date`, `dateTime` or `instant` data type can be annotated
with range annotations.

The `start` annotation describes the earliest instant that is considered to be
included in the value.

The `end` annotation describes the latest instant that is considered to be
included in the value.

For example, a value of `2014-06-01T12:05Z` would have a start of
`2014-06-01T12:05:00.000000Z` and an end of `2014-06-01T12:05:59.999999Z` at
microsecond precision.

Both the `start` and `end` annotations use the `int64` Parquet primitive type
and the `TIMESTAMP(isAdjustedToUTC=true, unit=MICROS)` logical type, with
values on the proleptic Gregorian calendar.

Here is an example of a schema that can accommodate Patient resources with
the `birthDate` element populated, along with annotation fields to store the
range.

```
message Patient {
  required binary resourceType (STRING);
  optional boolean __pof_v1;
  optional binary birthDate (STRING);
  optional group _birthDate {
    optional int64 __start (TIMESTAMP(isAdjustedToUTC=true, unit=MICROS));
    optional int64 __end (TIMESTAMP(isAdjustedToUTC=true, unit=MICROS));
  }
}
```

### Decimal values

The original values of decimals are stored as strings to preserve the precision
and scale of the original data.

Elements with a decimal type can use the `numeric` to store the value in a
numeric form.

The `numeric` annotation uses the `fixed_len_byte_array(16)` Parquet primitive
type, and the `DECIMAL(precision=38, scale=8)` logical type. It holds the
element's value rounded to eight fractional digits, the step size of the
FHIRPath `Decimal` type. Values are rounded using round-half-even.

Here is an example of a schema that can accommodate Observation resources with
an annotated decimal value:

```
message Observation {
  required binary resourceType (STRING);
  optional boolean __pof_v1;
  optional binary valueDecimal (STRING);
  optional group _valueDecimal {
    optional fixed_len_byte_array(16) __numeric (DECIMAL(precision=38, scale=8));
  }
}
```

### Quantity unit canonicalization

Elements of type Quantity can be annotated with the `canonical_value_exact`
and `canonical_code` annotations to add canonical unit and value information.
This can assist with comparison of Quantity values at query time.

For example, temperature observations in Celsius or Fahrenheit could be
canonicalized to Kelvin.

The `canonical_value_exact` annotation holds the value expressed in the
canonical unit, and the `canonical_code` annotation holds the code of the
canonical unit.

The `canonical_code` annotation uses the `binary` Parquet primitive type, and
the `STRING` logical type.

The `canonical_value_exact` annotation is represented as a group within the
schema that contains the following fields:

| Field name | Parquet primitive type   | Parquet logical type           |
|------------|--------------------------|--------------------------------|
| value      | fixed_len_byte_array(16) | DECIMAL(precision=38, scale=0) |
| scale      | INT32                    | INT(32, true)                  |

The `value` and `scale` fields hold the canonical value as a scaled integer. The
canonical value is equal to `value` × 10<sup>-`scale`</sup>, and its sign is the
sign of `value`. For example, a canonical value of `310.15` has a `value` of
31015 and a `scale` of 2.

Conversion to a canonical unit multiplies a value by a factor that depends on
the unit, so canonical values vary widely in magnitude. For example, `1 ng` is
`0.000000001 g`. A scaled integer holds up to 38 significant digits at any
magnitude below 10<sup>38</sup>, whereas a decimal with a fixed scale loses the
digits of a small value.

The following rules give each canonical value one representation, so that equal
canonical values are stored as equal fields:

- The `scale` field SHALL NOT be negative.
- The `scale` field SHALL be the smallest scale that can represent the canonical
  value. The `value` field therefore has no trailing zeros unless `scale` is 0,
  and a canonical value of zero has a `value` of 0 and a `scale` of 0.
- A canonical value that has more than 38 significant digits SHALL be rounded
  to 38 significant digits before the rules above are applied. A value that is
  halfway between the two nearest values SHALL be rounded away from zero.
- A canonical value that is 10<sup>38</sup> or greater in magnitude after
  rounding cannot be represented. The quantity SHALL NOT have canonical
  annotations, which means that its `canonical_value_exact` and
  `canonical_code` annotations are both null.
- A schema that contains one of the `value` and `scale` fields SHALL contain the
  other. Within a row, the two fields SHALL be either both null or both not
  null.

Here are some examples of quantities and their canonical annotations, using the
base units of UCUM as the canonical units. The `value` and `scale` columns are
the fields of the `canonical_value_exact` annotation:

| Quantity      | Canonical value                    | value                                  | scale | canonical_code |
|---------------|------------------------------------|----------------------------------------|-------|----------------|
| `1 ng`        | `0.000000001 g`                    | 1                                      | 9     | g              |
| `1000 pg`     | `0.000000001 g`                    | 1                                      | 9     | g              |
| `4 ng`        | `0.000000004 g`                    | 4                                      | 9     | g              |
| `250 pg`      | `0.00000000025 g`                  | 25                                     | 11    | g              |
| `0 mg`        | `0 g`                              | 0                                      | 0     | g              |
| `120 mm[Hg]`  | `15998640 g.m-1.s-2`               | 15998640                               | 0     | g.m-1.s-2      |
| `37 Cel`      | `310.15 K`                         | 31015                                  | 2     | K              |
| `98.6 [degF]` | `310.15 K`                         | 31015                                  | 2     | K              |
| `310.15 K`    | `310.15 K`                         | 31015                                  | 2     | K              |
| `1 [degF]`    | `255.927… K`, with the 7 recurring | 25592777777777777777777777777777777778 | 35    | K              |

Two quantities that have canonical annotations are equal if their
`canonical_code` annotations are equal, and the `value` and `scale` fields of
their `canonical_value_exact` annotations are equal. Canonical values that have
different codes cannot be compared.

To order two canonical values that have the same code, their scales need to be
aligned first. In the table above, `250 pg` has a greater `value` than `4 ng`
(25 against 4), but it is the smaller quantity: at a scale of 11, the two values
are 25 and 400. For this reason, the minimum and maximum statistics that Parquet
keeps for the `value` field do not describe the range of the canonical values.

Here is an example of a schema that can accommodate Observation resources with
a quantity value, along with annotation fields to store its canonical form and
the numeric form of its value (see [Decimal values](#decimal-values)):

```
message Observation {
  required binary resourceType (STRING);
  optional boolean __pof_v1;
  optional group valueQuantity {
    optional binary code (STRING);
    optional binary system (STRING);
    optional binary unit (STRING);
    optional binary value (STRING);
    optional group _value {
      optional fixed_len_byte_array(16) __numeric (DECIMAL(precision=38, scale=8));
    }
    optional group __canonical_value_exact {
      optional fixed_len_byte_array(16) value (DECIMAL(precision=38, scale=0));
      optional int32 scale (INT(32, true));
    }
    optional binary __canonical_code (STRING);
  }
}
```

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
  optional boolean __pof_v1;
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
  optional group _birthDate {
    optional int64 __start (TIMESTAMP(isAdjustedToUTC=true, unit=MICROS));
    optional int64 __end (TIMESTAMP(isAdjustedToUTC=true, unit=MICROS));
  }
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
  optional boolean __pof_v1;
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
  optional group _effectiveDateTime {
    optional int64 __start (TIMESTAMP(isAdjustedToUTC=true, unit=MICROS));
    optional int64 __end (TIMESTAMP(isAdjustedToUTC=true, unit=MICROS));
  }
  optional group valueQuantity {
    optional binary code (STRING);
    optional binary system (STRING);
    optional binary unit (STRING);
    optional binary value (STRING);
    optional group _value {
      optional fixed_len_byte_array(16) __numeric (DECIMAL(precision=38, scale=8));
    }
    optional group __canonical_value_exact {
      optional fixed_len_byte_array(16) value (DECIMAL(precision=38, scale=0));
      optional int32 scale (INT(32, true));
    }
    optional binary __canonical_code (STRING);
  }
}
```
