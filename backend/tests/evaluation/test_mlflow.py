import pytest
import os
import re
from minio import Minio
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
os.environ['MPLCONFIGDIR'] = "/tmp"
import matplotlib.pylab as plt
from sklearn.metrics import f1_score,precision_score,recall_score
from sklearn.model_selection import train_test_split
from mlflow.models.signature import infer_signature
import mlflow

class data_generator():

    def toy_dataset(self):
        col1 = np.arange(10)
        col2 = np.arange(10)
        target = ['A'] * 5 + ['B'] * 5
        df = pd.DataFrame(data={'col1': col1, 'col2': col2, 'target': target})
        return df

@pytest.fixture()
def minio_client():
    client = Minio(
        endpoint='minio:9000',
        access_key=os.getenv('MINIO_ROOT_USER'),
        secret_key=os.getenv('MINIO_ROOT_PASSWORD'),
        secure=False
    )
    return client

@pytest.fixture()
def minio_bucket(minio_client):
    if match:=re.match(r"s3://([^/]+)/?", os.getenv('MLFLOW_ARTIFACT_URI')):
        bucket_name = match.group(1)
    else:
        raise ValueError(f'no bucket name could be found')
    return bucket_name


@pytest.fixture()
def mlflow_experiment(minio_bucket):
    experiment_name = 'pytest'
    if mlflow.get_experiment_by_name(experiment_name) is None:
        mlflow.create_experiment(experiment_name, artifact_location=os.environ['MLFLOW_ARTIFACT_URI'])
    return experiment_name


def test_log_minio_artifact(mlflow_experiment,minio_client,minio_bucket):
    assert minio_client.bucket_exists(minio_bucket),f'bucket {minio_bucket} was not created' # minio_client.make_bucket(minio_bucket)
    mlflow.set_experiment(mlflow_experiment)
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI",'http://rag-modulo-mlflow-server-1:5000'))
    mlflow.autolog()
    with mlflow.start_run() as run:
        generator = data_generator()
        df = generator.toy_dataset()
        model = RandomForestClassifier(n_estimators=10)

        X_train, X_test, y_train, y_test = train_test_split(df[['col1', 'col2']],
                                                            df['target'], test_size=0.33,random_state=42)

        model.fit(X_train, y_train)
        y_hat = model.predict(X_test)
        score = f1_score(y_test, y_hat, pos_label='A')
        prec_score = precision_score(y_test, y_hat, pos_label='A')
        rec_score = recall_score(y_test, y_hat, pos_label='A')
        signature = infer_signature(df[['col1', 'col2']], df[['target']])
        mlflow.log_metrics({"f1_score":score,"precision_score":prec_score,"recall_score":rec_score})
        mlflow.sklearn.log_model(model, "model", registered_model_name='rag_modulo_test_model', signature=signature)
        run_id = run.info.run_id

        with plt.style.context(style='default'):
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(X_train.columns, model.feature_importances_)
            ax.set_title('feature importance')
            ax.set_xlabel('feature')
            ax.set_ylabel('importance')
            ax.set_xticks(range(len(X_train.columns)))
            ax.set_xticklabels(X_train.columns, rotation=45)
            plt.tight_layout()
        plt.close(fig)

        mlflow.log_figure(fig, "feature_importance.png")

    # verify metrics in tracking server (stored in postgres)
    logged_metrics = mlflow.get_run(run_id).data.metrics
    assert "f1_score" in logged_metrics, f"f1_score metric not found in mlflow run {run_id}."
    assert "training_log_loss" in logged_metrics, f"auto logged training_log_loss not found in mlflow run {run_id}."
    # verify artifacts in artifacts store (minio)
    objects = list(minio_client.list_objects(minio_bucket,recursive=True,prefix=run_id))
    artifacts = [f'{run_id}/artifacts/model/model.pkl',f'{run_id}/artifacts/feature_importance.png']
    assert all(artifact in (obj.object_name for obj in objects) for artifact in
               artifacts), f"Not all required artifacts are in mlflow minio bucket after run {run_id}."