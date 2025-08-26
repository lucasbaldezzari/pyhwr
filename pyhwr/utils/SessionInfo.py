class SessionInfo():
    def __init__(self, session_id, subject_id, session_name,
                 session_date, comments=None):
        self.session_id = session_id
        self.subject_id = subject_id
        self.session_name = session_name
        self.date = session_date
        self.comments = comments

    def __str__(self):
        return f"SesionInfo(id={self.id}, name={self.session_name}, date={self.date}"
    
    def __repr__(self):
        return self.__str__()
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "date": self.date,
            "subject_id": self.subject_id,
            "comments": self.comments
        }
    
    def __getitem__(self, key):
        return self.to_dict().get(key)
