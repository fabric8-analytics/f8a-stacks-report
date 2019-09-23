"""POM XML Template."""
pom_temp = """
<project xmlns="http://maven.apache.org/POM/4.0.0"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
  http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <groupId>org.example</groupId>
  <artifactId>jpademo</artifactId>
  <version>1.0</version>
  <packaging>jar</packaging>

  <scm>
      <connection>scm:git:ssh://my.git.server.internal/home/git/jpademo</connection>
      <developerConnection>scm:git:ssh://my.git.server.internal/home/git/jpademo</developerConnection>
  </scm>
  <ciManagement>
      <system>jenkins</system>
      <url>https://my.jenkins.internal/jenkins</url>
  </ciManagement>


  <name>jpademo</name>
  <url>http://maven.apache.org</url>
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>2.3.2</version>
                <configuration>
                    <source>1.6</source>
                    <target>1.6</target>
                </configuration>
            </plugin>

            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-jar-plugin</artifactId>
                <version>2.2</version>
                <executions>
                    <execution>
                        <goals>
                            <goal>jar</goal>
                        </goals>
                        <id>jar</id>
                    </execution>
                </executions>
                <configuration>
                      <archive>
                        <manifestFile>src/main/resources/Manifest.txt</manifestFile>
                        <manifest>
                          <addClasspath>true</addClasspath>

                          <mainClass>com.footballradar.jpademo.App</mainClass>

                        </manifest>
                      </archive>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-shade-plugin</artifactId>
                <version>1.4</version>
                    <executions>
                        <execution>
                                <phase>package</phase>
                                <goals>
                                        <goal>shade</goal>
                                </goals>
                        </execution>
                    </executions>
                    <configuration>
                            <finalName>${project.artifactId}-${project.version}</finalName>
                    </configuration>
            </plugin>

        </plugins>

    </build>

    <repositories>
    <repository>
      <url>http://download.java.net/maven/2/</url>
      <id>hibernate-support</id>
      <layout>default</layout>
      <name>Repository for library Library[hibernate-support]</name>
    </repository>
  </repositories>



  <properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>

  <dependencies>
  </dependencies>

 <distributionManagement>
    <repository>
        <id>My_Artifactory_Releases</id>
        <name>My_Artifactory-releases</name>
        <url>http://my.maven.repository.internal/artifactory/release</url>
    </repository>

    <snapshotRepository>
        <id>My_Artifactory_Snapshots</id>
        <name>My_Artifactory-snapshots</name>
        <url>http://my.maven.repository.internal/artifactory/snapshot</url>
    </snapshotRepository>

</distributionManagement>
</project>
"""
