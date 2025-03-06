variable "deployment_name" {
  description = "Name of the entity resolution deployment - used to derive schema and workflow names"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9_-]+$", var.deployment_name))
    error_message = "Deployment name must only contain alphanumeric characters, underscores, and hyphens."
  }
}

variable "schema" {
  description = "Entity Resolution schema attribute definitions"
  type = object({
    attributes = list(object({
      name        = string
      type        = string
      subtype     = optional(string, "NONE")
      glue_type   = optional(string, "string")
      match_key   = optional(bool, false)
      description = optional(string)
    }))
  })

  validation {
    condition     = length(var.schema.attributes) > 0
    error_message = "Schema must have at least one attribute."
  }

  # Validate attribute types
  validation {
    condition = alltrue([
      for attr in var.schema.attributes :
      contains(["TEXT", "NAME", "EMAIL", "PHONE_NUMBER", "ADDRESS", "DATE", "PERSON_IDENTIFIER", "ACCOUNT_NUMBER"], attr.type)
    ])
    error_message = "Attribute types must be one of: TEXT, NAME, EMAIL, PHONE_NUMBER, ADDRESS, DATE, PERSON_IDENTIFIER, ACCOUNT_NUMBER."
  }

  # Validate subtypes
  validation {
    condition = alltrue([
      for attr in var.schema.attributes :
      contains(["NONE", "FIRST", "LAST", "MOBILE", "HOME", "WORK", "STREET", "CITY", "STATE", "ZIP", "DOB", "SSN"], attr.subtype)
    ])
    error_message = "Attribute subtypes must be one of: NONE, FIRST, LAST, MOBILE, HOME, WORK, STREET, CITY, STATE, ZIP, DOB, SSN."
  }

  # Validate glue types
  validation {
    condition = alltrue([
      for attr in var.schema.attributes :
      contains(["string", "int", "bigint", "double", "float", "boolean", "date", "timestamp", "decimal"], attr.glue_type)
    ])
    error_message = "Glue types must be one of: string, int, bigint, double, float, boolean, date, timestamp, decimal."
  }
}
