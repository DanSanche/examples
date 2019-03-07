# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import kfp.dsl as dsl
import kfp.gcp as gcp
from kubernetes.client.models import V1EnvVar


@dsl.pipeline(
  name='MNIST',
  description='A pipeline to train and serve the MNIST example.'
)
def mnist_pipeline(model_export_dir='gs://your-bucket/export',
                   train_steps='200',
                   learning_rate='0.01',
                   batch_size='100'):
    train = dsl.ContainerOp(
            name='train',
            image='gcr.io/kubeflow-examples/mnist/model:v20190304-v0.2-176-g15d997b',
            arguments=[
                "/opt/model.py",
                "--tf-export-dir", model_export_dir,
                "--tf-train-steps", train_steps,
                "--tf-batch-size", batch_size,
                "--tf-learning-rate", learning_rate
            ]
    ).apply(gcp.use_gcp_secret('user-gcp-sa'))

    serve = dsl.ContainerOp(
        name='serve',
        image='gcr.io/ml-pipeline/ml-pipeline-kubeflow-deployer:7775692adf28d6f79098e76e839986c9ee55dd61',
        arguments=[
            '--model-export-path', model_export_dir,
            '--server-name', "mnist-service"
        ]
    ).apply(gcp.use_gcp_secret('user-gcp-sa'))
    serve.after(train)

    web_ui = dsl.ContainerOp(
        name='web-ui',
        image='gcr.io/kubeflow-examples/mnist/deploy-service:latest',
        arguments=[
            '--image', 'gcr.io/kubeflow-examples/mnist/web-ui:v20190304-v0.2-176-g15d997b-pipelines',
            '--name', 'web-ui',
            '--container-port', '5000',
            '--service-port', '80',
            '--service-type', "LoadBalancer"
        ]
    ).apply(gcp.use_gcp_secret('user-gcp-sa'))

    web_ui.after(serve)


if __name__ == '__main__':
    import kfp.compiler as compiler
    compiler.Compiler().compile(mnist_pipeline, __file__ + '.tar.gz')
