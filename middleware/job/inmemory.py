

class JobRepositoryMemory():
    '''Job service backed by an in-memory array for job storage. Used for
    testing'''
    def __init__(self):
        self._jobs = {}

    def create(self, job):
        job_id = job["id"]
        if(job_id not in self._jobs):
            # Add job if it is not already in job list
            self._jobs[job_id] = job
            return job
        else:
            return None

    def get_by_id(self, job_id):
        # Note: We could skip the whole if..else check for the existence of
        # job_id as a key as the dictionary.get() method returns None if the
        # key does not exist.
        if(job_id in self._jobs):
            return self._jobs.get(job_id)
        else:
            return None

    def update_job(self, job):
        job_id = job["id"]
        if(job_id in self._jobs):
            # Replace job if already in job list
            self._jobs[job_id] = job
            return job
        else:
            return None