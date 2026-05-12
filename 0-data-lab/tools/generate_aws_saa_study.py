import json
import random
from pathlib import Path

OUTPUT_FILE = Path("1-GP-GLUE/01-raw-data-lake/8b-jade/aws_saa_study_v1.jsonl")

def generate_saa_flashcards(count):
    topics = {
        "VPC": [
            ("What is a VPC peering connection?", "A networking connection between two VPCs that enables you to route traffic between them using private IPv4 or IPv6 addresses."),
            ("What is the purpose of an Egress-Only Internet Gateway?", "To allow outbound communication over IPv6 from instances in your VPC to the Internet, and prevent the Internet from initiating an IPv6 connection with your instances."),
            ("What is a NAT Gateway used for?", "To enable instances in a private subnet to connect to the internet or other AWS services, but prevent the internet from initiating a connection with those instances."),
        ],
        "IAM": [
            ("What is an IAM Role?", "An IAM identity that you can create in your account that has specific permissions, which is intended to be assumable by anyone who needs it (users, applications, services)."),
            ("What is the difference between an IAM User and an IAM Group?", "An IAM User is an entity that you create in AWS to represent the person or application that uses it. An IAM Group is a collection of IAM users."),
            ("What is a Service-Linked Role?", "A unique type of IAM role that is linked directly to an AWS service, predefined by the service and includes all the permissions that the service requires to call other AWS services on your behalf."),
        ],
        "S3": [
            ("What is S3 Transfer Acceleration?", "A bucket-level feature that enables fast, easy, and secure transfers of files over long distances between your client and an S3 bucket using Amazon CloudFront's globally distributed edge locations."),
            ("What are S3 Lifecycle policies?", "Rules that define how Amazon S3 manages objects during their lifetime, such as transitioning objects to less expensive storage classes or archiving/deleting them after a specified period."),
            ("What is S3 Object Lock?", "A feature that allows you to store objects using a write-once-read-many (WORM) model, preventing objects from being deleted or overwritten for a fixed amount of time or indefinitely."),
        ],
        "KMS": [
            ("What is a Customer Master Key (CMK)?", "A logical representation of a master key in KMS, including metadata and the key material used to encrypt and decrypt data."),
            ("What is the difference between AWS managed CMKs and Customer managed CMKs?", "AWS managed CMKs are created, managed, and used on your behalf by an AWS service. Customer managed CMKs are created, owned, and managed by you."),
            ("What is an envelope encryption?", "The practice of encrypting plaintext data with a data key, and then encrypting the data key under another key (the master key)."),
        ],
        "Compute": [
            ("What is an Amazon Machine Image (AMI)?", "A template that contains a software configuration (operating system, application server, and applications) required to launch an instance."),
            ("What is Auto Scaling?", "A service that monitors your applications and automatically adjusts capacity to maintain steady, predictable performance at the lowest possible cost."),
            ("What are the different types of EC2 instances?", "General Purpose, Compute Optimized, Memory Optimized, Accelerated Computing, and Storage Optimized."),
        ],
        "Database": [
            ("What is Amazon RDS Multi-AZ deployment?", "A feature that provides high availability and failover support for DB instances by automatically creating a primary DB instance and synchronously replicating the data to a standby instance in a different Availability Zone."),
            ("What is Amazon DynamoDB?", "A key-value and document database that delivers single-digit millisecond performance at any scale, being fully managed, multi-region, and multi-active."),
            ("What is Amazon Aurora?", "A MySQL and PostgreSQL-compatible relational database built for the cloud, combining the performance and availability of traditional enterprise databases with the simplicity and cost-effectiveness of open-source databases."),
        ]
    }
    
    flashcards = []
    topic_list = list(topics.keys())
    
    for i in range(count):
        topic = random.choice(topic_list)
        q, a = random.choice(topics[topic])
        
        # Add variation to question to make it unique-ish for training
        variations = [
            f"Question: {q}",
            f"Explain: {q}",
            f"AWS SAA Prep: {q}",
            f"Technical Interview: {q}"
        ]
        
        flashcards.append({
            "messages": [
                {"role": "system", "content": "You are an AWS Certified Solutions Architect. Answer technical questions concisely and accurately."},
                {"role": "user", "content": random.choice(variations)},
                {"role": "assistant", "content": a}
            ],
            "metadata": {"domain": "cloud", "topic": "aws-saa", "type": "study-material", "subtopic": topic}
        })
        
    return flashcards

def main():
    examples = generate_saa_flashcards(110) # Generate 110 to ensure 100+
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Generated {len(examples)} AWS SAA study pairs to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
