locals {
  # Common identifier attributes
  id_attributes = [
    {
      name        = "id"
      type        = "PERSON_IDENTIFIER"
      glue_type   = "string"
      match_key   = true
      description = "Primary identifier"
    }
  ]

  # Common name attributes
  name_attributes = [
    {
      name        = "first_name"
      type        = "NAME"
      subtype     = "FIRST"
      glue_type   = "string"
      match_key   = true
      description = "First name"
    },
    {
      name        = "last_name"
      type        = "NAME"
      subtype     = "LAST"
      glue_type   = "string"
      match_key   = true
      description = "Last name"
    }
  ]

  # Common contact attributes
  contact_attributes = [
    {
      name        = "email"
      type        = "EMAIL"
      glue_type   = "string"
      match_key   = true
      description = "Email address"
    },
    {
      name        = "phone"
      type        = "PHONE_NUMBER"
      glue_type   = "string"
      match_key   = true
      description = "Phone number"
    }
  ]

  # Common address attributes
  address_attributes = [
    {
      name        = "address"
      type        = "ADDRESS"
      glue_type   = "string"
      match_key   = false
      description = "Full address"
    }
  ]

  # Common timestamp attributes
  timestamp_attributes = [
    {
      name        = "created_at"
      type        = "DATE"
      glue_type   = "timestamp"
      match_key   = false
      description = "Creation timestamp"
    }
  ]

  # Template for person schema
  person_template = {
    schema_name = "person"
    description = "Generic person schema"
    attributes = concat(
      local.id_attributes,
      local.name_attributes,
      local.contact_attributes,
      local.timestamp_attributes
    )
  }

  # Template for customer schema
  customer_template = {
    schema_name = "customer"
    description = "Customer schema for matching"
    attributes = concat(
      local.id_attributes,
      local.name_attributes,
      local.contact_attributes,
      local.address_attributes,
      local.timestamp_attributes,
      [
        {
          name        = "customer_type"
          type        = "TEXT"
          glue_type   = "string"
          match_key   = false
          description = "Customer type"
        }
      ]
    )
  }

  # Template for employee schema
  employee_template = {
    schema_name = "employee"
    description = "Employee schema for matching"
    attributes = concat(
      local.id_attributes,
      local.name_attributes,
      local.contact_attributes,
      local.address_attributes,
      local.timestamp_attributes,
      [
        {
          name        = "employee_id"
          type        = "PERSON_IDENTIFIER"
          glue_type   = "string"
          match_key   = true
          description = "Employee ID"
        },
        {
          name        = "department"
          type        = "TEXT"
          glue_type   = "string"
          match_key   = false
          description = "Department"
        }
      ]
    )
  }
}

output "person_template" {
  description = "Base template for person entities"
  value       = local.person_template
}

output "customer_template" {
  description = "Template for customer entities"
  value       = local.customer_template
}

output "employee_template" {
  description = "Template for employee entities"
  value       = local.employee_template
}

output "id_attributes" {
  description = "Common identifier attributes"
  value       = local.id_attributes
}

output "name_attributes" {
  description = "Common name attributes"
  value       = local.name_attributes
}

output "contact_attributes" {
  description = "Common contact attributes"
  value       = local.contact_attributes
}

output "address_attributes" {
  description = "Common address attributes"
  value       = local.address_attributes
}

output "timestamp_attributes" {
  description = "Common timestamp attributes"
  value       = local.timestamp_attributes
}
