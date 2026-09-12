from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, firstName, lastName, email, password, role):
        self.id = id
        self.firstName = firstName
        self.lastName = lastName
        self.email = email
        self.password = password
        self.role = role

    @property
    def fullName(self):
        return f"{self.firstName} {self.lastName}"

    def isManager(self):
        return self.role == 'manager'

    def isStudent(self):
        return self.role == 'student'