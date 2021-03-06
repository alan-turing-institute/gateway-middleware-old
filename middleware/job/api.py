import json_merge_patch
from flask_restful import Resource, abort, request
from flask import current_app, send_from_directory
from middleware.job_information_manager import job_information_manager as JIM
from middleware.job.schema import (job_to_json, json_to_job,
                                   job_to_summary_json,
                                   case_to_summary_json)
from middleware.job.models import case_to_job, copy_job_fields
import arrow
import os


class JobApi(Resource):
    """API for reading (GET), amending (PUT/PATCH) and deleting (DELETE)
    individual jobs"""
    def __init__(self, **kwargs):
        # Inject job service
        self.jobs = kwargs['job_repository']
        self.middleware_only_fields = kwargs.get('middleware_only_fields')

    def abort_if_not_found(self, job_id):
        if not self.jobs.exists(job_id):
            abort(404, message="Job {} not found".format(job_id))

    def get(self, job_id):
        self.abort_if_not_found(job_id)
        job = self.jobs.get_by_id(job_id)

        # Update job status from job manager and save updated job
        # TODO: Test this directly? (we already test the update_job_status()
        # method to ensure it returns an exception that will be passed to
        # client)
        manager = JIM(job, job_repository=self.jobs)
        job.status = manager.update_job_status()
        job = self.jobs.update(job)

        job_json = job_to_json(job)
        return job_json, 200, {'Content-Type': 'application/json'}

    def put(self, job_id):
        # Require Job to exist in order to amend it
        job_old = self.jobs.get_by_id(job_id)
        if job_old is None:
            self.abort_if_not_found(job_id)
        # Get Job JSON if present
        job_json = request.json

        if job_json is None:
            abort(400, message="Message body could not be parsed as JSON")
        # Try parsing Job JSON to Job object
        try:
            job_new = json_to_job(job_json)
        except:
            abort(400, message="Message body is not valid Job JSON")
        # Ignore any middleware only fields by copying the existing values
        copy_job_fields(source=job_old, destination=job_new,
                        fields=self.middleware_only_fields)
        # Check job_id route parameter consistent with provided Job data
        if job_id != job_new.id:
            abort(409, message="Job ID in URL ({}) does not match job "
                               "ID in message JSON ({}).".format(job_id,
                                                                 job_new.id))
        # Persist updated Job object to repository
        updated_job = self.jobs.update(job_new)
        if updated_job is None:
            abort(404, message="Job {} not found".format(job_new.id))
        else:
            return job_to_json(updated_job), 200, {'Content-Type':
                                                   'application/json'}

    def _patch_job(self, job_id, request):
        # Require Job to exist in order to amend it
        job_old = self.jobs.get_by_id(job_id)
        if job_old is None:
            self.abort_if_not_found(job_id)
        # Get Job JSON if present
        job_partial_json = request.json
        if job_partial_json is None:
            abort(400, message="Message body could not be parsed as JSON")
        # Require ID field to be present in JSON body to enforce match with
        # ID provided in route parameter
        job_id_json = job_partial_json.get("id")
        if job_id_json is None:
            abort(400, message="No ID found in Job JSON")
        # Check job_id route parameter consistent with provided Job data
        # We do not allow ID to be changed by patch()
        if job_id != job_id_json:
            abort(409, message="Job ID in URL ({}) does not match job "
                               "ID in message JSON ({}).".format(job_id,
                                                                 job_id_json))
        # Try and patch existing Job from partial Job
        job_old_json = job_to_json(job_old)
        job_new_json = json_merge_patch.merge(job_old_json, job_partial_json)
        # Try parsing Job JSON to Job object
        try:
            job_new = json_to_job(job_new_json)
        except:
            abort(400, message="Message body is not valid Job JSON")
        # Ignore any middleware only fields by copying the existing values
        copy_job_fields(source=job_old, destination=job_new,
                        fields=self.middleware_only_fields)
        # Check job_id route parameter consistent with provided Job data
        if job_id != job_new.id:
            abort(409, message="Job ID in URL ({}) does not match job "
                               "ID in message JSON ({}).".format(job_id,
                                                                 job_new.id))
        # Persist updated Job object to repository
        updated_job = self.jobs.update(job_new)
        if updated_job is None:
            abort(404, message="Job {} not found".format(job_new.id))
        else:
            return updated_job

    def patch(self, job_id):
        updated_job = self._patch_job(job_id, request)
        return job_to_json(updated_job), 200, {'Content-Type':
                                               'application/json'}

    def delete(self, job_id):
        # Require job to exist in order to delete it
        job = self.jobs.get_by_id(job_id)
        if job is None:
            self.abort_if_not_found(job_id)
        # Delete job
        self.jobs.delete(job_id)
        deleted_job = self.jobs.get_by_id(job_id)
        return deleted_job, 204


class JobsApi(Resource):
    """API for listing a collection of jobs (GET) and creating a new
    individual job (POST)"""
    def __init__(self, **kwargs):
        # Inject job service
        self.jobs = kwargs['job_repository']

    def get(self):

        def list_job_summary_json(job_id):
            job = self.jobs.get_by_id(job_id)
            # Update job status from job manager and save updated job
            # TODO: Test this directly? (we already test the update_job_status
            # method to ensure it returns an exception that will be passed to
            # client)
            manager = JIM(job, job_repository=self.jobs)
            job.status = manager.update_job_status()
            job = self.jobs.update(job)
            # Return summary Job data as JSON
            summary_json = job_to_summary_json(job)
            return summary_json

        job_ids = self.jobs.list_ids()
        summary_list = [list_job_summary_json(job_id) for job_id in job_ids]
        return {"jobs": summary_list}, 200,
        {'Content-Type': 'application/json'}

    def post(self):
        job_json = request.json
        if job_json is None:
            abort(400, message="Message body could not be parsed as JSON")
        # Try parsing Job JSON to Job object
        try:
            job = json_to_job(job_json)
        except:
            abort(400, message="Message body is not valid Job JSON")
        if self.jobs.exists(job.id):
            abort(409, message="Job with ID {} already "
                               "exists".format(job.id))
        else:
            # Set certain job properties when first persisted
            job.creation_datetime = arrow.utcnow()
            job.status = "Draft"
            job = self.jobs.create(job)
            return job_to_json(job), 200, {'Content-Type': 'application/json'}


class CasesApi(Resource):
    """API endpoint called to get a list of cases (GET)"""
    def __init__(self, **kwargs):
        self.cases = kwargs['case_repository']

    def get(self):

        def list_case_summary_json(case_id):
            case = self.cases.get_by_id(case_id)
            summary_json = case_to_summary_json(case)
            return summary_json

        case_ids = self.cases.list_ids()
        summary_list = [list_case_summary_json(case_id) for
                        case_id in case_ids]
        return {"cases": summary_list}, 200,
        {'Content-Type': 'application/json'}


class CaseApi(Resource):
    """API endpoint called to get specific case job template (GET)"""

    def __init__(self, **kwargs):
        # Inject case service
        self.cases = kwargs['case_repository']

    def abort_if_not_found(self, case_id):
        if not self.cases.exists(case_id):
            abort(404, message="Case {} not found".format(case_id))

    def get(self, case_id):
        self.abort_if_not_found(case_id)
        case = self.cases.get_by_id(case_id)
        job = case_to_job(case)
        job_json = job_to_json(job)
        return job_json, 200, {'Content-Type': 'application/json'}


class SetupApi(Resource):
    """API endpoint called to setup a job on the cluster (POST)"""
    def __init__(self, **kwargs):
        # Inject job service
        self.jobs = kwargs['job_repository']
        self.middleware_only_fields = kwargs.get('middleware_only_fields')

    def abort_if_not_found(self, job_id):
        if not self.jobs.exists(job_id):
            abort(404, message="Job {} not found".format(job_id))

    def post(self, job_id):
        job_api = JobApi(job_repository=self.jobs,
                         middleware_only_fields=self.middleware_only_fields)
        updated_job = job_api._patch_job(job_id, request)
        manager = JIM(updated_job, job_repository=self.jobs)
        return manager.setup()


class ProgressApi(Resource):
    """
    API endpoint called to check the progress of a job
    on the cluster (POST)
    """
    def __init__(self, **kwargs):
        # Inject job service
        self.jobs = kwargs['job_repository']

    def get(self, job_id):

        job = self.jobs.get_by_id(job_id)
        if job:
            manager = JIM(job, job_repository=self.jobs)
            return manager.progress()
        else:
            abort(404, message="Job {} not found".format(job_id))


class DataApi(Resource):
    """API endpoint called to check the data of a job on the cluster (POST)"""
    def __init__(self, **kwargs):
        # Inject job service
        self.jobs = kwargs['job_repository']

    def get(self, job_id):

        job = self.jobs.get_by_id(job_id)
        if job:
            manager = JIM(job, job_repository=self.jobs)
            return manager.data()
        else:
            abort(404, message="Job {} not found".format(job_id))


class CancelApi(Resource):
    """API endpoint called to cancel a job on the cluster (POST)"""
    def __init__(self, **kwargs):
        # Inject job service
        self.jobs = kwargs['job_repository']

    def post(self, job_id):

        job = self.jobs.get_by_id(job_id)
        if job:
            manager = JIM(job, job_repository=self.jobs)
            return manager.cancel()
        else:
            abort(404, message="Job {} not found".format(job_id))


class RunApi(Resource):
    """API endpoint called to run a job on the cluster (POST)"""
    def __init__(self, **kwargs):
        # Inject job service
        self.jobs = kwargs['job_repository']
        self.middleware_only_fields = kwargs.get('middleware_only_fields')

    def abort_if_not_found(self, job_id):
        if not self.jobs.exists(job_id):
            abort(404, message="Job {} not found".format(job_id))

    def post(self, job_id):
        job_api = JobApi(job_repository=self.jobs,
                         middleware_only_fields=self.middleware_only_fields)
        updated_job = job_api._patch_job(job_id, request)
        updated_job.start_datetime = arrow.utcnow()
        manager = JIM(updated_job, job_repository=self.jobs)
        return manager.run()


class ThumbnailApi(Resource):
    """API endpoint called to return static files (GET)"""
    def __init__(self, **kwargs):
        pass

    def get(self, path):
        static_folder = current_app.static_folder
        img_folder = os.path.join(static_folder, 'img')
        return send_from_directory(img_folder, path,
                                   mimetype='image/png',
                                   as_attachment=False)
