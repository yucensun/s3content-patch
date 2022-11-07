from fsspec.asyn import sync
import os

from s3contents.gcs.gcs_fs import GCSFS
from s3contents.genericmanager import GenericContentsManager
from s3contents.ipycompat import Unicode


class GCSContentsManager(GenericContentsManager):

    project = Unicode(
        help="GCP Project", allow_none=True, default_value=None
    ).tag(config=True, env="JPYNB_GCS_PROJECT")
    token = Unicode(
        help="Path to the GCP token", allow_none=True, default_value=None
    ).tag(config=True, env="JPYNB_GCS_TOKEN_PATH")

    region_name = Unicode("us-east-1", help="Region name").tag(
        config=True, env="JPYNB_GCS_REGION_NAME"
    )
    bucket = Unicode("notebooks", help="Bucket name to store notebooks").tag(
        config=True, env="JPYNB_GCS_BUCKET"
    )

    prefix = Unicode("", help="Prefix path inside the specified bucket").tag(
        config=True
    )
    separator = Unicode("/", help="Path separator").tag(config=True)

    def __init__(self, *args, **kwargs):
        super(GCSContentsManager, self).__init__(*args, **kwargs)

        self._fs = GCSFS(
            log=self.log,
            project=self.project,
            token=self.token,
            bucket=self.bucket,
            prefix=self.prefix,
            separator=self.separator,
        )
        
    def _convert_file_records(self, paths):
        """
        Applies _notebook_model_from_s3_path or _file_model_from_s3_path to each entry of `paths`,
        depending on the result of `guess_type`.
        """
        ret = []
        for path in paths:
            # path = self.fs.remove_prefix(path, self.prefix)  # Remove bucket prefix from paths
            if os.path.basename(path) == self.fs.dir_keep_file:
                continue
            type_ = self.guess_type(path, allow_directory=True)
            if type_ == "notebook":
                ret.append(self._notebook_model_from_path(path, False))
            elif type_ == "file":
                ret.append(self._file_model_from_path(path, False, None))
            elif type_ == "directory":
                ret.append(self._directory_model_from_path(path, False))
            else:
                self.do_error("Unknown file type %s for file '%s'" % (type_, path), 500)
        return ret

    def _list_contents(self, model, prefixed_path):
        """List the contents in prefixed_path."""
        files_gcs_detail = sync(
            self.fs.fs.loop, self.fs.fs._ls, prefixed_path
        )
        # filter out the current directory
        filtered_files_gcs_detail = list(
            filter(
                lambda detail: os.path.basename(detail)
                != "",
                files_gcs_detail,
            )
        )
        self.log.debug(f"\n listed files: {filtered_files_gcs_detail}")

        for file_gcs_detail in filtered_files_gcs_detail:
            self.log.debug(
                f"\n file_gcs_detail: {file_gcs_detail}"
                f"\n lstat={self.fs.lstat(file_gcs_detail)}"
            )

        converted_files_gcs_detail = self._convert_file_records(filtered_files_gcs_detail)
        model["content"] = converted_files_gcs_detail
        return model
    
