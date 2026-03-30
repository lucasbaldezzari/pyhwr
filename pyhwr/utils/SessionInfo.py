class SessionInfo():
    """
    Clase para almacenar información relevante de la sesión,
    como el ID de la sesión, el nombre descriptivo, la fecha, el ID del sujeto,
    comentarios adicionales, y campos para generar el nombre de archivo BIDS (sub, ses, task, run, suffix).
    """
    def __init__(self, sub=1, ses=1, task="ejecutada", run=1, suffix="eeg",
                 session_id = None, subject_id = None, session_name = None,
                 session_date=None, bids_file=None, comments=None):
        """
        session_id: ID de la sesión (ej: "ses-01")
        subject_id: ID del sujeto (ej: "sub-01")
        session_name: Nombre descriptivo de la sesión (ej: "sesion_pre")
        session_date: Fecha de la sesión (ej: "2024-06-01")
        sub, ses, task, run, suffix: campos para generar el nombre de archivo BIDS
        comments: comentarios adicionales (opcional)
        """
        self.session_id = ses if session_id is None else session_id
        self.subject_id = sub if subject_id is None else subject_id
        self.session_name = task if session_name is None else session_name
        self.date = session_date
        self.comments = comments
        self.sub = sub
        self.ses = ses
        self.task = task
        self.run = run
        self.suffix = suffix
        self.bids_file = bids_file

    def __str__(self):
        return f"SesionInfo(id={self.session_id}, name={self.session_name}, date={self.date})"
    
    def __repr__(self):
        return self.__str__()
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "date": self.date,
            "subject_id": self.subject_id,
            "comments": self.comments,
            "sub": self.sub,
            "ses": self.ses,
            "task": self.task,
            "run": self.run,
            "suffix": self.suffix,
            "bids_file": self.bids_file,
            }
    
    def __getitem__(self, key):
        return self.to_dict().get(key)
