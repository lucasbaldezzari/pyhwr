class SesionInfo():
    def __init__(self, session_id, session_name,
                 session_date, run_number, subject_name, comments=None):
        self.id = session_id
        self.name = session_name
        self.date = session_date
        self.run_number = run_number
        self.subject_name = subject_name
        self.comments = comments

    def __str__(self):
        return f"SesionInfo(id={self.id}, name={self.name}, date={self.date}"
    
    def __repr__(self):
        return self.__str__()
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date,
            "run_number": self.run_number,
            "subject_name": self.subject_name,
            "comments": self.comments
        }
    
    def __getitem__(self, key):
        return self.to_dict().get(key)
