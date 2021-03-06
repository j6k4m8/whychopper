# whychopper

https://whychopper.getneutrality.org/

what is that low-flying aircraft outside my house, and for whom do they work?

<img width="1010" alt="image" src="https://user-images.githubusercontent.com/693511/96068188-61cb4b00-0e69-11eb-88d5-407746b1c2d3.png">

## Setting up your own

You'll need a zappa settings file. Here is an example (`zappa_settings.json`):

```json
{
    "dev": {
        "app_function": "main.APP",
        "environment_variables": {
            "PGEOCODE_DATA_DIR": "/tmp/pgeo"
        },
        "aws_region": "us-east-1",
        "runtime": "python3.7"
    }
}
```
