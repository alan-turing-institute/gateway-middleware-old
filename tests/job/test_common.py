from middleware.job.common import JobApi
from middleware.job.inmemory import JobRepositoryMemory
from middleware.app import create_app
import unittest
import pytest
from werkzeug.exceptions import NotFound
import json


@pytest.fixture
def test_client(job_repository=JobRepositoryMemory()):
    app = create_app(job_repository)
    return app.test_client()


def response_to_json(response):
    return json.loads(response.get_data(as_text=True))


class TestJobApi(unittest.TestCase):

    def test_abort_if_not_found_throws_notfound_exception(self):
        jobs = JobRepositoryMemory()
        api = JobApi(job_repository=jobs)
        job_id = "d769843b-6f37-4939-96c7-c382c3e74b46"
        with pytest.raises(NotFound):
            api.abort_if_not_found(job_id)

    def test_get_for_existing_job_returns_job_with_200_status(self):
        jobs = JobRepositoryMemory()
        # Create job
        job_id = "d769843b-6f37-4939-96c7-c382c3e74b46"
        job = {"id": job_id,
               "parameters": {"height": 3, "width": 4, "depth": 5}}
        jobs.create(job)
        client = test_client(jobs)
        job_response = client.get("/job/{}".format(job_id))
        assert job_response.status_code == 200
        assert response_to_json(job_response) == job

    def test_get_for_nonexistent_job_returns_error_with_404_status(self):
        jobs = JobRepositoryMemory()
        client = test_client(jobs)
        job_id = "d769843b-6f37-4939-96c7-c382c3e74b46"
        job_response = client.get("/job/{}".format(job_id))
        error_message = {"message": "Job {} not found".format(job_id)}
        assert job_response.status_code == 404
        assert response_to_json(job_response) == error_message

    def test_get_with_no_job_id_returns_error_with_404_status(self):
        jobs = JobRepositoryMemory()
        client = test_client(jobs)
        job_response = client.get("/job/")
        assert job_response.status_code == 404
        # No content check as we are expecting the standard 404 error message
        # TODO: Get the 404 response defined for the app and compare it here


class TestJobsApi(object):

    def test_post_for_nonexistent_job_returns_job_with_200_status(self):
        jobs = JobRepositoryMemory()
        # Create job
        job_id = "d769843b-6f37-4939-96c7-c382c3e74b46"
        job = {"id": job_id,
               "parameters": {"height": 3, "width": 4, "depth": 5}}
        client = test_client(jobs)
        job_response = client.post("/jobs", data=json.dumps(job),
                                   content_type='application/json')
        assert job_response.status_code == 200
        assert response_to_json(job_response) == job
        assert jobs.get_by_id(job_id) == job

    def test_post_for_existing_job_returns_error_with_409_status(self):
        jobs = JobRepositoryMemory()
        # Create job
        job_id = "d769843b-6f37-4939-96c7-c382c3e74b46"
        job_existing = {"id": job_id, "parameters": {"height": 3, "width": 4,
                        "depth": 5}}
        jobs.create(job_existing)
        job_new = {"id": job_id, "parameters": {"blue": "high",
                   "green": "low"}}
        client = test_client(jobs)
        job_response = client.post("/jobs", data=json.dumps(job_new),
                                   content_type='application/json')
        error_message = {"message": "Job with ID {} already "
                         "exists".format(job_id)}
        assert job_response.status_code == 409
        assert response_to_json(job_response) == error_message
        assert jobs.get_by_id(job_id) == job_existing

    def test_post_with_none_returns_error_with_400_status(self):
        jobs = JobRepositoryMemory()
        client = test_client(jobs)
        job_response = client.post("/jobs", data=json.dumps(None),
                                   content_type='application/json')
        error_message = {"message": "Message body could not be parsed as JSON"}
        assert job_response.status_code == 400
        assert response_to_json(job_response) == error_message
        assert len(jobs._jobs) == 0