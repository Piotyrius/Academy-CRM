from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginAnonThrottle(AnonRateThrottle):
    scope = 'login_anon'


class LoginUserThrottle(UserRateThrottle):
    scope = 'login_user'


class PasswordResetAnonThrottle(AnonRateThrottle):
    scope = 'password_reset_anon'


class LogoutThrottle(UserRateThrottle):
    scope = 'logout'



