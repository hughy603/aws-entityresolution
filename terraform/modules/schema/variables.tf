variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, test, staging, prod)"
  type        = string
}

variable "schema_name" {
  description = "Name of the Entity Resolution schema (defaults to project-environment-schema)"
  type        = string
  default     = ""
}

variable "schema_definition" {
  description = "Schema definition for Entity Resolution"
  type = object({
    attributes = list(object({
      name      = string
      type      = string
      sub_type  = optional(string)
      match_key = optional(bool)
      required  = optional(bool)
      array     = optional(bool)
    }))
  })
}

variable "schema_templates" {
  description = "Map of predefined schema templates"
  type = map(object({
    attributes = list(object({
      name      = string
      type      = string
      sub_type  = optional(string)
      match_key = optional(bool)
      required  = optional(bool)
      array     = optional(bool)
    }))
  }))
  default = {}
}

variable "schema_template_name" {
  description = "Name of the schema template to use"
  type        = string
  default     = ""
}

variable "use_schema_template" {
  description = "Whether to use a predefined schema template"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
