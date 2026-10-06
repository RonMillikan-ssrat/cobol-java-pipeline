#!/usr/bin/env python3
"""
Apache Beam pipeline for COBOL-to-Java conversion validation on Dataflow
Maps local orchestrator pattern to distributed Beam transforms
"""

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import WorkerOptions
import json
import subprocess
import time
from datetime import datetime
import uuid

class GenerateEBCDICFn(beam.DoFn):
    """Parallelize EBCDIC generation across workers"""
    def process(self, job_config):
        try:
            job_id = job_config.get('job_id', str(uuid.uuid4()))
            seed = job_config.get('seed', None)
            start_time = time.time()  # Track start time for entire job

            # Run generator
            cmd = f"python3 1_generate_ebcdic_weather.py --seed {seed}" if seed else "python3 1_generate_ebcdic_weather.py"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                yield {
                    'job_id': job_id,
                    'step': 'generate_ebcdic',
                    'status': 'SUCCESS',
                    'timestamp': datetime.now().isoformat(),
                    'seed': seed,
                    'start_time': start_time
                }
            else:
                yield {
                    'job_id': job_id,
                    'step': 'generate_ebcdic',
                    'status': 'FAILED',
                    'error': result.stderr,
                    'start_time': start_time
                }
        except Exception as e:
            yield {'status': 'ERROR', 'error': str(e), 'start_time': time.time()}

class RunCOBOLReaderFn(beam.DoFn):
    """Run COBOL reader (actual COBOL implementation)"""
    def process(self, step_result):
        if step_result.get('status') != 'SUCCESS':
            yield step_result
            return

        try:
            result = subprocess.run(
                "python3 2_cobol_weather_reader.py",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                step_result['step'] = 'run_cobol_reader'
                step_result['status'] = 'SUCCESS'
                yield step_result
            else:
                step_result['step'] = 'run_cobol_reader'
                step_result['status'] = 'FAILED'
                step_result['error'] = result.stderr
                yield step_result
        except Exception as e:
            step_result['status'] = 'ERROR'
            step_result['error'] = str(e)
            yield step_result

class RunJavaReaderFn(beam.DoFn):
    """Run Java reader (converted from COBOL)"""
    def process(self, step_result):
        if step_result.get('status') != 'SUCCESS':
            yield step_result
            return

        try:
            # Compile Java
            compile_result = subprocess.run(
                "javac ConvertedWeatherReader.java",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if compile_result.returncode != 0:
                step_result['step'] = 'run_java_reader'
                step_result['status'] = 'FAILED'
                step_result['error'] = f"Compilation failed: {compile_result.stderr}"
                yield step_result
                return

            # Run Java
            run_result = subprocess.run(
                "java ConvertedWeatherReader",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if run_result.returncode == 0:
                step_result['step'] = 'run_java_reader'
                step_result['status'] = 'SUCCESS'
                yield step_result
            else:
                step_result['step'] = 'run_java_reader'
                step_result['status'] = 'FAILED'
                step_result['error'] = run_result.stderr
                yield step_result
        except Exception as e:
            step_result['status'] = 'ERROR'
            step_result['error'] = str(e)
            yield step_result

class CompareOutputsFn(beam.DoFn):
    """Compare COBOL and Java outputs (byte-for-byte)"""
    def process(self, step_result):
        if step_result.get('status') != 'SUCCESS':
            yield step_result
            return

        try:
            result = subprocess.run(
                "python3 4_compare_outputs.py",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse comparison results
            try:
                # Assume output contains JSON results
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'VERDICT' in line:
                        verdict = 'PASS' if 'PASS' in line else 'FAIL'
                        step_result['step'] = 'compare_outputs'
                        step_result['status'] = 'SUCCESS'
                        step_result['validation_verdict'] = verdict
                        # Calculate elapsed time from start
                        start_time = step_result.get('start_time', time.time())
                        step_result['execution_time_seconds'] = time.time() - start_time
                        yield step_result
                        return
            except:
                pass

            step_result['step'] = 'compare_outputs'
            step_result['status'] = 'SUCCESS' if result.returncode == 0 else 'FAILED'
            step_result['validation_verdict'] = 'PASS' if result.returncode == 0 else 'FAIL'
            # Calculate elapsed time from start
            start_time = step_result.get('start_time', time.time())
            step_result['execution_time_seconds'] = time.time() - start_time
            yield step_result
        except Exception as e:
            step_result['status'] = 'ERROR'
            step_result['error'] = str(e)
            yield step_result

class WriteToBigQueryFn(beam.DoFn):
    """Format results for BigQuery with proper type casting"""
    def process(self, result):
        try:
            # Format for BigQuery insertion - ensure all types match schema
            bq_row = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',  # ISO 8601 UTC format
                'job_id': str(result.get('job_id', 'unknown')),
                'iteration': int(result.get('iteration', 1)),  # Track iteration number
                'validation_verdict': str(result.get('validation_verdict', 'UNKNOWN')),
                'execution_time_seconds': float(result.get('execution_time_seconds', 0.0)),
                'weather_map_match_percentage': float(100.0 if result.get('validation_verdict') == 'PASS' else 0.0),
                'output_bytes_cobol': int(result.get('output_bytes_cobol', 0)),
                'output_bytes_java': int(result.get('output_bytes_java', 0)),
                'status': str(result.get('status', 'UNKNOWN')),
                'error_message': str(result.get('error', '')) if result.get('error') else None
            }
            yield bq_row
        except Exception as e:
            # Log formatting errors but don't fail
            print(f"Error formatting row: {e}")
            print(f"Input: {result}")
            raise

def run_pipeline(argv=None):
    """Run the Dataflow pipeline"""

    pipeline_options = PipelineOptions(argv)
    pipeline_options.view_as(WorkerOptions).autoscaling_algorithm = 'THROUGHPUT_BASED'
    # Use custom Docker image with COBOL, Java, and dependencies pre-installed
    pipeline_options.view_as(WorkerOptions).worker_harness_container_image = 'gcr.io/cobol-to-java-converter-o/dataflow-worker:latest'

    with beam.Pipeline(options=pipeline_options) as p:
        # Source: Read job configurations from Pub/Sub or a file
        # For testing, we'll create inline configs
        job_configs = (
            p
            | 'CreateJobConfigs' >> beam.Create([
                {'job_id': f'job-{i}', 'seed': i}
                for i in range(10)
            ])
        )

        # Pipeline stages
        results = (
            job_configs
            | 'GenerateEBCDIC' >> beam.ParDo(GenerateEBCDICFn())
            | 'RunCOBOL' >> beam.ParDo(RunCOBOLReaderFn())
            | 'RunJava' >> beam.ParDo(RunJavaReaderFn())
            | 'CompareOutputs' >> beam.ParDo(CompareOutputsFn())
        )

        # Format for BigQuery and write
        formatted_results = (
            results
            | 'FormatForBigQuery' >> beam.ParDo(WriteToBigQueryFn())
        )

        formatted_results | 'WriteToBigQuery' >> beam.io.WriteToBigQuery(
            table='cobol_java_conversions.conversion_results',
            create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
        )

if __name__ == '__main__':
    import sys
    run_pipeline(sys.argv[1:])
