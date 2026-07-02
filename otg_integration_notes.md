# OTG Integration Notes

- Methods
    1. Converted to state changes (idempotent approach)

- RoCEv2 settings
    1. Most settings moved to devices/rocev2
    1. Some settings moved onto qp object (still under rocev2)

- Platforms:
    1. Old model issue: Cannot support multiple platforms of the same type (e.g. two custom platforms, for two different vendors)
        - Change platforms to be identified by name instead of type
        - Platforms becomes an dictionary of name to platform definition.
        - Each platform definition has only one variant defined
    1. Todo:
        - Describe in conversion guide
        - Add validation to disallow multiple platforms of same type (until middleware can handle it)


## Name Changes

    Trial -> AiWorkload
    