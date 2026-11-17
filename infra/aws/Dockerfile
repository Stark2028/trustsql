FROM trustsql:local
USER root
RUN pip install --target /lambda mangum==0.19.0
RUN cp -a /usr/local/lib/python3.12/site-packages/. /lambda/ && rm -rf /lambda/pip /lambda/pip-*.dist-info
COPY infra/aws/lambda_handler.py /lambda/lambda_handler.py
COPY src/trustsql /lambda/trustsql
COPY infra/aws/package_lambda.py /package_lambda.py
RUN python /package_lambda.py
CMD ["python", "-c", "print('Copy /artifacts/function.zip from this image')"]
