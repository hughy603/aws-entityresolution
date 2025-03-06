variable "template_name" {
  description = "Name of the schema template to use"
  type        = string
}

variable "config" {
  description = "Configuration object for the template module"
  type = object({
    project_name = string
    environment  = string
    tags         = map(string)
  })
}
