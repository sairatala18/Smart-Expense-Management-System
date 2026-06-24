import csv
import os

EMPLOYEE_FILE = "employees.csv"
TEMP_FILE = "employees_temp.csv"

def migrate_emails():
    if not os.path.exists(EMPLOYEE_FILE):
        print("Error: employees.csv not found.")
        return

    with open(EMPLOYEE_FILE, 'r') as f_in, open(TEMP_FILE, 'w', newline='') as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        
        count = 0
        for row in reader:
            if row:
                # If row is missing columns, fill them up to index 5 (Email)
                while len(row) < 6:
                    if len(row) == 4: # Missing Emp_ID
                        row.append(f"EM_OLD_{count}")
                    if len(row) == 5: # Missing Email
                        row.append(f"{row[0].lower().replace(' ', '')}@company.com")
                    count += 1
                writer.writerow(row)

    # Replace the old file with the updated one
    os.replace(TEMP_FILE, EMPLOYEE_FILE)
    print(f"Migration complete! Added placeholders for {count} records.")

if __name__ == "__main__":
    migrate_emails()