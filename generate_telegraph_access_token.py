from telegraph import Telegraph

telegraph = Telegraph()
telegraph.create_account(short_name="LyriphonBot")

print(telegraph.get_access_token())
