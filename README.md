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

## Primitive extensions and internal identifiers

Extensions and the internal identifier of each primitive element can be
represented within the schema as a field within the schema with the same name
prepended with an underscore.

This field is represented as a group within the schema that can contain the
following fields:

| Field name | Parquet primitive type | Parquet logical type                                                            |
|------------|------------------------|---------------------------------------------------------------------------------|
| id         | binary                 | STRING                                                                          |
| extension  | group                  | See Extension ([Complex and backbone elements](#complex-and-backbone-elements)) |

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
type, and the `DECIMAL(precision=32, scale=6)` logical type.

Here is an example of a schema that can accommodate Observation resources with
an annotated decimal value:

```
message Observation {
  required binary resourceType (STRING);
  optional binary valueDecimal (STRING);
  optional fixed_len_byte_array(16) __valueDecimal_numeric (DECIMAL(precision=32, scale=6));
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
| value      | fixed_len_byte_array(16) | DECIMAL(precision=32, scale=6) |
| code       | binary                   | STRING                         |
