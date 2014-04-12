from gaesessions import SessionMiddleware
 

def webapp_add_wsgi_middleware(app): 
    app = SessionMiddleware(app, no_datastore=False ,cookie_key="xYu76Wqqxvc8iItyqpavlfgyTr^7&8)oPINMYHG$£qw2333Upqw-09&^GdSaklk") 
    return app
