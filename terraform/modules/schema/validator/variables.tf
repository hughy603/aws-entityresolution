variable "schema_file" {
  description = "Path to the schema file to validate"
  type        = string
  default     = null
}

variable "entity_attributes" {
  description = "List of entity attributes to validate against"
  type = list(object({
    name     = string
    type     = string
    required = bool
  }))
}

variable "config" {
  description = "Configuration object for the validator module"
  type = object({
    project_name = string
    environment  = string
    tags         = map(string)
  })
}
